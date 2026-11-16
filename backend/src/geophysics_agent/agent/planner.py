"""方案生成的原子操作：出草案、修复、规则兜底。

有意**不**在这里写循环——``plan → verify → repair`` 的主循环放在
``agent.runner`` 里，让 agent 的控制流只有一个入口，便于阅读与测试。
"""

from __future__ import annotations

from geophysics_agent.agent.llm import LLMClient
from geophysics_agent.agent.prompts import SYSTEM_PROMPT, build_plan_user, build_repair_user
from geophysics_agent.domain.analysis import AssessmentBundle
from geophysics_agent.domain.conditions import SiteConditions
from geophysics_agent.domain.enums import METHOD_ORDER, Method, Role, Suitability
from geophysics_agent.domain.plan import PlanDraft, PlanItem, Risk, Violation
from geophysics_agent.domain.schemas import Evidence


def generate_draft(
    llm: LLMClient,
    *,
    message: str,
    conditions: SiteConditions,
    bundle: AssessmentBundle,
    evidence: list[Evidence],
) -> PlanDraft:
    """让模型基于评估表生成方案草案。可能抛 ``LLMError``。"""
    return llm.complete_json(
        system=SYSTEM_PROMPT,
        user=build_plan_user(
            message=message, conditions=conditions, bundle=bundle, evidence=evidence
        ),
        schema=PlanDraft,
    )


def repair_draft(
    llm: LLMClient,
    *,
    conditions: SiteConditions,
    bundle: AssessmentBundle,
    draft: PlanDraft,
    violations: list[Violation],
) -> PlanDraft:
    """把校验问题回灌给模型，要求其修正。可能抛 ``LLMError``。"""
    return llm.complete_json(
        system=SYSTEM_PROMPT,
        user=build_repair_user(
            conditions=conditions, bundle=bundle, draft=draft, violations=violations
        ),
        schema=PlanDraft,
    )


def fallback_plan(bundle: AssessmentBundle) -> PlanDraft:
    """不依赖模型的规则方案，保证任何情况下都有物理上成立的输出。"""
    items: list[PlanItem] = []
    primary_method = bundle.recommended_primary[0] if bundle.recommended_primary else None

    if primary_method is None:
        feasible = [
            method for method in bundle.recommended_support if bundle.methods[method].feasible
        ]
        feasible.sort(key=lambda method: bundle.methods[method].depth_margin, reverse=True)
        primary_method = feasible[0] if feasible else None

    if primary_method is not None:
        primary = bundle.methods[primary_method]
        mitigation: str | None = None
        if primary.suitability is Suitability.CONSTRAINED:
            mitigation = "受限条件需用试验剖面标定，并只在其有效深度段内使用"
        elif primary.interference_notes:
            mitigation = "避开干扰源作业窗口，并做重复观测以识别假异常"
        if primary_method is Method.DAS:
            mitigation = "需钻孔内光缆或既有通信光缆，否则该方法无法开展"
        resolution = (
            f"{primary.vertical_resolution_m:g} m"
            if primary.vertical_resolution_m is not None
            else "无垂向分辨能力"
        )
        items.append(
            PlanItem(
                method=primary_method,
                role=Role.PRIMARY,
                rationale=(
                    f"{primary.method_cn} 深度余量 {primary.depth_margin:.2f}×、"
                    f"垂向分辨率约 {resolution}，对{bundle.target_cn}的物性响应为：{bundle.target_contrast}"
                ),
                mitigation=mitigation,
            )
        )

    for method in bundle.recommended_support:
        if method == primary_method:
            continue
        if len([item for item in items if item.role is Role.SUPPORT]) >= 2:
            break
        assessment = bundle.methods[method]
        items.append(
            PlanItem(
                method=method,
                role=Role.SUPPORT,
                rationale=f"{assessment.method_cn} 可提供交叉验证：{assessment.suitability_reason}",
            )
        )

    assigned = {item.method for item in items}
    for method in METHOD_ORDER:
        if method in assigned:
            continue
        assessment = bundle.methods[method]
        if not assessment.feasible:
            reason = (
                f"深度不可行：最大探测深度 {assessment.max_depth_m:g} m "
                f"小于目标埋深 {bundle.design_depth_m:g} m"
            )
        elif assessment.suitability is Suitability.NOT_APPLICABLE:
            reason = f"物性不匹配：{assessment.suitability_reason}"
        else:
            reason = f"本次不作为主要手段：{assessment.suitability_reason}"
        items.append(PlanItem(method=method, role=Role.EXCLUDED, rationale=reason))
        assigned.add(method)

    risks: list[Risk] = []
    if primary_method is not None:
        for limitation in bundle.methods[primary_method].limitations[:3]:
            risks.append(
                Risk(
                    risk=limitation[:80],
                    impact="可能导致异常漏判或误判",
                    response="用辅助方法交叉验证，并在异常段布置钻孔",
                )
            )
    risks.append(
        Risk(
            risk="物探解释的多解性",
            impact="异常体性质可能与推断不符",
            response="以钻孔与原位测试标定，不把物探结果直接当作设计依据",
        )
    )

    primary_cn = bundle.methods[primary_method].method_cn if primary_method else "方法试验"
    return PlanDraft(
        summary=(
            f"针对{bundle.target_cn}（{bundle.medium_cn}，{bundle.depth_range}），"
            f"建议以{primary_cn}为主，配合辅助方法交叉验证，并以钻探验证异常。"
        ),
        items=items,
        risks=risks[:5],
        verification=[
            "每个异常段布置至少 1 个钻孔，核对异常体性质与埋深",
            "开工前在已知段做试验剖面，标定采集参数与信噪比",
        ],
        missing_information=["场地可布设长度与施工作业窗口"],
    )
