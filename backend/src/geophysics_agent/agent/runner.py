"""Agent 主循环（编排层）。

一次请求的完整流程：

    intake（规则抽取） → 会话合并 → 完整性检查
        ├─ 不完整 → 澄清
        └─ 完整 → 检索证据 → 确定性评估 → 模型草案 → 规则校验
                     ├─ 有 error → 修复（≤N 次）
                     └─ 仍失败 / 模型不可用 → 规则兜底（degraded）
                → 按最终主方法重算外业设计 → 渲染正文 → 写回会话

这条链路就是"agent"的定义所在：**目标状态、工具调用、反馈闭环、自我校验、失败降级**，
每一步都记录在 ``trace`` 里，可回放、可测试。
"""

from __future__ import annotations

import logging
import time
import uuid

from geophysics_agent.agent.intake import build_questions, extract_conditions
from geophysics_agent.agent.llm import LLMClient, LLMError
from geophysics_agent.agent.planner import fallback_plan, generate_draft, repair_draft
from geophysics_agent.agent.renderer import render, render_clarification
from geophysics_agent.agent.session_store import SessionStore
from geophysics_agent.agent.trace import TraceRecorder
from geophysics_agent.agent.verifier import has_errors, verify
from geophysics_agent.analysis import assess, build_design
from geophysics_agent.analysis.tables import DISCLAIMER
from geophysics_agent.core.config import Settings, get_settings
from geophysics_agent.domain.conditions import SiteConditions
from geophysics_agent.domain.plan import SurveyPlan
from geophysics_agent.domain.schemas import (
    RecommendResponse,
    Usage,
    build_condition_view,
)
from geophysics_agent.knowledge.retriever import Retriever
from geophysics_agent.knowledge.semantic import build_semantic_client

logger = logging.getLogger(__name__)


class AgentRunner:
    """把各层组件编排成一次完整的 agent 运行。"""

    def __init__(
        self,
        *,
        settings: Settings,
        llm: LLMClient | None,
        retriever: Retriever | None = None,
        sessions: SessionStore | None = None,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._retriever = retriever or Retriever(
            top_k=settings.knowledge_top_k,
            semantic=build_semantic_client(settings),
        )
        self._sessions = sessions or SessionStore(
            max_sessions=settings.session_max_sessions,
            ttl_minutes=settings.session_ttl_minutes,
        )

    # ------------------------------------------------------------------ 公开入口
    def run(
        self,
        message: str,
        conversation_id: str | None = None,
        *,
        reset: bool = False,
    ) -> RecommendResponse:
        """处理一次请求并返回完整响应。"""
        started = time.perf_counter()
        trace = TraceRecorder()

        conversation = conversation_id or str(uuid.uuid4())
        if reset:
            self._sessions.clear(conversation)
        state = self._sessions.get_or_create(conversation)

        # 1) 条件抽取与会话合并 ------------------------------------------------
        with trace.step("intake", "解析自然语言场景") as handle:
            update = extract_conditions(message)
            base = SiteConditions() if reset else state.conditions
            conditions = base.merge(update)
            handle.detail = conditions.summary()

        # 2) 完整性检查 → 澄清 ------------------------------------------------
        if not conditions.is_complete():
            questions = build_questions(conditions)
            trace.add("clarify", "warn", f"缺少关键字段，提出 {len(questions)} 个问题")
            self._remember(state, conditions, primary=None)
            return self._clarification(conditions, questions, trace, conversation, started)

        # 3) 检索课程证据 ------------------------------------------------------
        with trace.step("retrieve", "混合检索课程知识（BM25+向量+Rerank）") as handle:
            retrieval = self._retriever.search(message)
            handle.detail = (
                f"命中 {len(retrieval.evidence)} 条，相关性={retrieval.quality}，"
                f"最高分={retrieval.top_score:.2f}"
            )
            if retrieval.quality != "strong":
                handle.warn(f"证据相关性{retrieval.quality}，不能作为强依据")

        # 4) 确定性评估（工具调用）--------------------------------------------
        with trace.step("assess", "八种方法深度/分辨率/成本评估") as handle:
            bundle = assess(conditions)
            handle.detail = (
                f"设计埋深 {bundle.design_depth_m:g} m，"
                f"推荐主方法={'、'.join(m.cn for m in bundle.recommended_primary) or '无'}"
            )

        # 5) 模型草案 ---------------------------------------------------------
        notices: list[str] = []
        degraded = False
        with trace.step("plan", "模型生成方案草案") as handle:
            if self._llm is None:
                draft = fallback_plan(bundle)
                degraded = True
                notices.append("未配置可用模型，已使用规则方案")
                handle.warn("模型不可用，跳过草案生成")
            else:
                try:
                    draft = generate_draft(
                        self._llm,
                        message=message,
                        conditions=conditions,
                        bundle=bundle,
                        evidence=retrieval.evidence,
                    )
                    handle.detail = f"草案含 {len(draft.items)} 个方法条目"
                except LLMError as exc:
                    draft = fallback_plan(bundle)
                    degraded = True
                    notices.append(f"模型调用失败，已回退规则方案：{exc}")
                    handle.fail(str(exc))

        # 6) 规则校验 + 修复循环 ----------------------------------------------
        with trace.step("verify", "校验方案与评估表是否一致") as handle:
            violations = verify(draft, conditions, bundle)
            errors = [item for item in violations if item.severity == "error"]
            handle.detail = f"error={len(errors)}，warning={len(violations) - len(errors)}"
            if errors:
                handle.warn(f"发现 {len(errors)} 个必须修复的问题")

        repairs = 0
        while (
            has_errors(violations) and not degraded and repairs < self._settings.planner_max_repairs
        ):
            repairs += 1
            with trace.step(f"repair#{repairs}", "把校验问题回灌模型修正") as handle:
                try:
                    draft = repair_draft(
                        self._llm,  # type: ignore[arg-type]
                        conditions=conditions,
                        bundle=bundle,
                        draft=draft,
                        violations=[item for item in violations if item.severity == "error"],
                    )
                except LLMError as exc:
                    handle.fail(f"修复调用失败：{exc}")
                    notices.append(f"修复调用失败：{exc}")
                    break
                violations = verify(draft, conditions, bundle)
                remaining = sum(1 for item in violations if item.severity == "error")
                handle.detail = f"修复后剩余 error={remaining}"

        if has_errors(violations):
            with trace.step("fallback", "回退到确定性规则方案") as handle:
                draft = fallback_plan(bundle)
                violations = verify(draft, conditions, bundle)
                degraded = True
                notices.append("模型方案未通过校验，已回退规则方案")
                handle.warn("规则方案已接管")

        # 7) 按最终主方法重算外业设计 -----------------------------------------
        primary_item = draft.primary()
        primary_method = primary_item.method if primary_item else None
        with trace.step("design", "按主方法计算测线与工作量") as handle:
            design = build_design(
                primary_method,
                bundle.methods[primary_method] if primary_method else None,
                site_length_m=conditions.site_length_m,
                depth_m=bundle.design_depth_m,
                target=conditions.target,
            )
            handle.detail = (
                f"总测线 {design.total_line_km:g} km，成本指数 {design.relative_cost_index:.1f}"
                if primary_method
                else "无主方法，未给出外业设计"
            )

        # 8) 组装并渲染 --------------------------------------------------------
        warnings = list(bundle.warnings) + notices
        warnings.extend(
            f"[{item.code}] {item.message}" for item in violations if item.severity == "warning"
        )
        plan = SurveyPlan(
            summary=draft.summary,
            items=draft.items,
            risks=draft.risks,
            verification=draft.verification,
            missing_information=draft.missing_information,
            violations=violations,
            degraded=degraded,
        )
        with trace.step("render", "渲染结构化正文") as handle:
            plan.narrative = render(
                plan=plan,
                conditions=conditions,
                bundle=bundle,
                design=design,
                evidence=retrieval.evidence,
                quality=retrieval.quality,
                warnings=warnings,
            )
            handle.detail = f"{len(plan.narrative)} 字符"

        self._remember(state, conditions, primary=primary_method)

        return RecommendResponse(
            mode="degraded" if degraded else "agent",
            conversation_id=conversation,
            answer=plan.narrative,
            conditions=conditions,
            conditions_view=build_condition_view(conditions),
            missing_information=draft.missing_information,
            plan=plan,
            assessments=bundle.ordered(),
            design=design,
            evidence=retrieval.evidence,
            evidence_quality=retrieval.quality,
            warnings=warnings,
            trace=trace.steps,
            usage=self._usage(),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            disclaimer=DISCLAIMER,
        )

    # ------------------------------------------------------------------ 内部方法
    def _clarification(
        self,
        conditions: SiteConditions,
        questions: list[str],
        trace: TraceRecorder,
        conversation: str,
        started: float,
    ) -> RecommendResponse:
        return RecommendResponse(
            mode="clarification",
            conversation_id=conversation,
            answer=render_clarification(conditions, questions),
            needs_clarification=True,
            questions=questions,
            conditions=conditions,
            conditions_view=build_condition_view(conditions),
            missing_information=conditions.missing_critical(),
            trace=trace.steps,
            usage=self._usage(),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            disclaimer=DISCLAIMER,
        )

    def _usage(self) -> Usage:
        if self._llm is None:
            return Usage()
        stats = self._llm.usage
        return Usage(
            calls=stats.calls,
            prompt_tokens=stats.prompt_tokens,
            completion_tokens=stats.completion_tokens,
        )

    def _remember(self, state, conditions: SiteConditions, primary: str | None) -> None:
        state.conditions = conditions
        state.turns += 1
        state.last_primary = primary
        self._sessions.save(state)


_runner: AgentRunner | None = None


def build_runner(settings: Settings | None = None) -> AgentRunner:
    """按配置构造（或复用）全局 runner；测试可用依赖覆盖替换。"""
    global _runner
    if _runner is None:
        resolved = settings or get_settings()
        from geophysics_agent.agent.llm import build_llm

        _runner = AgentRunner(settings=resolved, llm=build_llm(resolved))
    return _runner
