"""Agent 主循环测试：正常、澄清、修复、降级、多轮记忆。"""

from __future__ import annotations

from collections.abc import Callable

from geophysics_agent.agent.intake import extract_conditions
from geophysics_agent.agent.llm import LLMError
from geophysics_agent.agent.planner import fallback_plan
from geophysics_agent.agent.runner import AgentRunner
from geophysics_agent.analysis import assess
from geophysics_agent.domain.enums import Method, Role
from geophysics_agent.domain.plan import PlanDraft, PlanItem, Risk
from geophysics_agent.domain.scenarios import get_scenario
from tests.conftest import FakeLLM

KARST_QUERY = get_scenario("4").query


def _bad_draft() -> PlanDraft:
    """一个物理上错误的方案：15 m 溶洞用磁法作主方法。"""
    return PlanDraft(
        summary="用磁法直接找溶洞",
        items=[
            PlanItem(method=Method.MAGNETIC, role=Role.PRIMARY, rationale="磁法快速"),
            PlanItem(method=Method.DC, role=Role.SUPPORT, rationale="作为辅助手段补充"),
        ],
        risks=[Risk(risk="多解性", impact="误判", response="钻孔验证")],
        verification=["继续观察"],
        missing_information=[],
    )


def test_no_llm_falls_back_to_rule_plan(make_runner: Callable[..., AgentRunner]) -> None:
    response = make_runner(None).run(KARST_QUERY)

    assert response.mode == "degraded"
    assert response.plan is not None
    assert response.plan.degraded is True
    assert response.plan.primary_method() is Method.DC
    assert len(response.plan.items) == 8
    assert "规则引擎" in response.answer


def test_agent_mode_with_valid_draft(make_runner: Callable[..., AgentRunner]) -> None:
    conditions = extract_conditions(KARST_QUERY)
    bundle = assess(conditions)
    llm = FakeLLM([fallback_plan(bundle)])

    response = make_runner(llm).run(KARST_QUERY)

    assert response.mode == "agent"
    assert response.plan is not None
    assert response.plan.degraded is False
    assert response.usage.calls >= 1
    assert llm.calls == 1


def test_llm_error_degrades_gracefully(make_runner: Callable[..., AgentRunner]) -> None:
    llm = FakeLLM(error=LLMError("连接超时"))

    response = make_runner(llm).run(KARST_QUERY)

    assert response.mode == "degraded"
    assert any("模型调用失败" in warning for warning in response.warnings)


def test_invalid_draft_is_repaired(make_runner: Callable[..., AgentRunner]) -> None:
    conditions = extract_conditions(KARST_QUERY)
    bundle = assess(conditions)
    llm = FakeLLM([_bad_draft(), fallback_plan(bundle)])

    response = make_runner(llm).run(KARST_QUERY)

    assert llm.calls == 2, "应当触发一次修复调用"
    assert response.mode == "agent"
    assert response.plan is not None
    assert response.plan.primary_method() is not Method.MAGNETIC
    assert any(step.step.startswith("repair") for step in response.trace)


def test_unrepairable_draft_falls_back(make_runner: Callable[..., AgentRunner]) -> None:
    llm = FakeLLM([_bad_draft(), _bad_draft()])

    response = make_runner(llm).run(KARST_QUERY)

    assert response.mode == "degraded"
    assert response.plan is not None
    assert any("未通过校验" in warning for warning in response.warnings)


def test_incomplete_input_asks_for_clarification(
    make_runner: Callable[..., AgentRunner],
) -> None:
    response = make_runner(None).run("我想做个物探，看看这下面有什么东西。")

    assert response.mode == "clarification"
    assert response.needs_clarification is True
    assert len(response.questions) == 3
    assert response.plan is None


def test_multi_turn_merges_conditions(make_runner: Callable[..., AgentRunner]) -> None:
    runner = make_runner(None)
    first = runner.run("场地为砂土，需要圈定含水层，埋深 30 m。")
    assert first.conditions.depth is not None
    assert first.conditions.depth.design_depth_m == 30.0

    second = runner.run(
        "那如果埋深改成 60 m，方案要怎么调整？", conversation_id=first.conversation_id
    )

    assert second.conversation_id == first.conversation_id
    assert second.conditions.target is first.conditions.target
    assert second.conditions.medium is first.conditions.medium
    assert second.conditions.depth is not None
    assert second.conditions.depth.design_depth_m == 60.0


def test_conversations_are_isolated(make_runner: Callable[..., AgentRunner]) -> None:
    runner = make_runner(None)
    runner.run("场地为砂土，需要圈定含水层，埋深 30 m。")

    fresh = runner.run("那如果埋深改成 60 m，方案要怎么调整？")

    assert fresh.mode == "clarification", "新会话不应继承上一会话的条件"


def test_reset_clears_conversation(make_runner: Callable[..., AgentRunner]) -> None:
    runner = make_runner(None)
    first = runner.run("场地为砂土，需要圈定含水层，埋深 30 m。")

    reset = runner.run("埋深改成 60 m", conversation_id=first.conversation_id, reset=True)

    assert reset.mode == "clarification"
