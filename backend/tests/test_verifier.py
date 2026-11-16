"""校验器测试：每条规则都要能用构造出的错误方案触发。"""

from __future__ import annotations

from geophysics_agent.agent.intake import extract_conditions
from geophysics_agent.agent.verifier import has_errors, verify
from geophysics_agent.analysis import assess
from geophysics_agent.domain.conditions import DepthRange, SiteConditions
from geophysics_agent.domain.enums import Budget, Interference, Medium, Method, Role, Target
from geophysics_agent.domain.plan import PlanDraft, PlanItem, Risk

RISK = Risk(risk="多解性", impact="误判", response="钻孔验证")


def _conditions(target: Target, medium: Medium, depth: float, **kwargs) -> SiteConditions:
    return SiteConditions(
        target=target,
        medium=medium,
        depth=DepthRange(min_m=0.0, max_m=depth),
        **kwargs,
    )


def _draft(*items: PlanItem, verification: list[str] | None = None) -> PlanDraft:
    return PlanDraft(
        summary="测试用方案摘要，仅用于校验器单元测试",
        items=list(items),
        risks=[RISK, RISK.model_copy(), RISK.model_copy()],
        verification=verification or ["每个异常段布置钻孔验证"],
        missing_information=[],
    )


def test_missing_primary_is_error() -> None:
    conditions = _conditions(Target.KARST, Medium.LIMESTONE, 15.0)
    bundle = assess(conditions)
    draft = _draft(PlanItem(method=Method.DC, role=Role.SUPPORT, rationale="仅作辅助"))

    codes = {item.code for item in verify(draft, conditions, bundle)}

    assert "V001" in codes


def test_infeasible_primary_is_error() -> None:
    conditions = _conditions(Target.KARST, Medium.LIMESTONE, 15.0)
    bundle = assess(conditions)
    draft = _draft(PlanItem(method=Method.MAGNETIC, role=Role.PRIMARY, rationale="尝试磁法"))

    violations = verify(draft, conditions, bundle)
    codes = {item.code for item in violations}

    assert {"V002", "V003"} <= codes
    assert has_errors(violations)


def test_constrained_primary_requires_mitigation() -> None:
    conditions = _conditions(Target.KARST, Medium.LIMESTONE, 15.0)
    bundle = assess(conditions)
    draft = _draft(PlanItem(method=Method.GPR, role=Role.PRIMARY, rationale="用雷达打深部"))

    codes = {item.code for item in verify(draft, conditions, bundle)}

    assert "V005" in codes


def test_interference_requires_mitigation() -> None:
    conditions = extract_conditions(
        "城市道路填土场地查找管线，埋深 2 m，地表有钢筋混凝土地面，附近有 10 kV 电力线。"
    )
    bundle = assess(conditions)
    draft = _draft(PlanItem(method=Method.GPR, role=Role.PRIMARY, rationale="雷达最合适"))

    codes = {item.code for item in verify(draft, conditions, bundle)}

    assert "V009" in codes


def test_verification_must_contain_actionable_step() -> None:
    conditions = _conditions(Target.PLUME, Medium.CLAY, 12.0)
    bundle = assess(conditions)
    draft = _draft(
        PlanItem(method=Method.DC, role=Role.PRIMARY, rationale="电法识别低阻异常"),
        verification=["继续观察"],
    )

    codes = {item.code for item in verify(draft, conditions, bundle)}

    assert "V012" in codes


def test_das_primary_requires_fiber_source() -> None:
    conditions = _conditions(Target.LIQUEFACTION, Medium.SOFT_SOIL, 20.0)
    bundle = assess(conditions)
    draft = _draft(PlanItem(method=Method.DAS, role=Role.PRIMARY, rationale="光纤测振"))

    codes = {item.code for item in verify(draft, conditions, bundle)}

    assert "V011" in codes


def test_excluding_a_primary_method_is_error() -> None:
    conditions = extract_conditions(
        "城市道路填土场地查找地下管线，埋深 2 m，地表有钢筋混凝土地面。"
    )
    bundle = assess(conditions)
    draft = _draft(
        PlanItem(
            method=Method.MAGNETIC,
            role=Role.PRIMARY,
            rationale="用磁法找金属管",
            mitigation="避开钢筋",
        ),
        PlanItem(method=Method.GPR, role=Role.EXCLUDED, rationale="不用雷达"),
    )

    codes = {item.code for item in verify(draft, conditions, bundle)}

    assert "V007" in codes


def test_low_budget_conflicts_with_high_cost_design() -> None:
    conditions = _conditions(
        Target.KARST,
        Medium.LIMESTONE,
        15.0,
        budget=Budget.LOW,
        site_length_m=3000.0,
        interference=[Interference.TERRAIN],
    )
    bundle = assess(conditions)
    assert bundle.design.cost_band == "高", "测试前提：长测线下成本档应为高"
    draft = _draft(
        PlanItem(
            method=Method.DC,
            role=Role.PRIMARY,
            rationale="电法覆盖深度足够",
            mitigation="做地形改正",
        )
    )

    codes = {item.code for item in verify(draft, conditions, bundle)}

    assert "V014" in codes


def test_marginal_primary_is_warning_when_nothing_is_adequate() -> None:
    """40 m 灰岩溶洞：所有方法余量都不足 1.15×，此时只提示、不强制打回。"""
    conditions = _conditions(Target.KARST, Medium.LIMESTONE, 40.0)
    bundle = assess(conditions)
    draft = _draft(
        PlanItem(
            method=Method.DC,
            role=Role.PRIMARY,
            rationale="采用最大排列长度的 ERT 尽可能覆盖目标",
            mitigation="只在其有效深度段内解释，深部以钻孔控制",
        )
    )

    violations = verify(draft, conditions, bundle)

    assert not has_errors(violations)
    assert any(item.code == "V004" and item.severity == "warning" for item in violations)


def test_clean_plan_has_no_errors() -> None:
    conditions = _conditions(Target.PLUME, Medium.CLAY, 12.0)
    bundle = assess(conditions)
    draft = _draft(
        PlanItem(method=Method.DC, role=Role.PRIMARY, rationale="电法对低阻污染羽敏感"),
        PlanItem(method=Method.SURFACE_WAVE, role=Role.SUPPORT, rationale="辅助分层"),
        PlanItem(method=Method.GPR, role=Role.EXCLUDED, rationale="黏土中衰减过大"),
    )

    violations = verify(draft, conditions, bundle)

    assert not has_errors(violations)
