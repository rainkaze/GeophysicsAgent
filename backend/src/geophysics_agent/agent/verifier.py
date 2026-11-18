"""方案校验器：agent 的"自检"环节。

大模型输出方案后，这里用**纯规则**检查它是否与确定性评估冲突。
发现的 ``error`` 会触发修复循环；修复失败则回退到规则方案并标记降级。
这是本项目"模型不能凭空决定"的制度保障。
"""

from __future__ import annotations

from geophysics_agent.domain.analysis import AssessmentBundle
from geophysics_agent.domain.conditions import SiteConditions
from geophysics_agent.domain.enums import Budget, Method, Role, Suitability, Target
from geophysics_agent.domain.plan import PlanDraft, Violation

#: 可作为 UXO 主方法的工具
_UXO_PRIMARY: frozenset[Method] = frozenset({Method.MAGNETIC, Method.FDEM})
#: 验证动作必须命中的关键词
_VERIFICATION_KEYWORDS = ("钻孔", "钻探", "CPT", "静力触探", "试验剖面", "原位测试", "开挖验证")
#: DAS 依赖光缆的字样
_FIBER_KEYWORDS = ("光缆", "钻孔", "光纤")


def verify(
    draft: PlanDraft,
    conditions: SiteConditions,
    bundle: AssessmentBundle,
) -> list[Violation]:
    """校验方案草案，返回全部问题（error 优先）。"""
    violations: list[Violation] = []
    primary_item = draft.primary()

    # --- 结构：必须有且只有一个主方法（评估器确实有推荐时）---
    if primary_item is None:
        if bundle.recommended_primary:
            violations.append(
                Violation(
                    code="V001",
                    severity="error",
                    message=(
                        "方案没有指定主方法（评估器推荐："
                        + "、".join(method.cn for method in bundle.recommended_primary)
                        + "）"
                    ),
                )
            )
        else:
            violations.append(
                Violation(
                    code="V001",
                    severity="warning",
                    message="八种演示方法在当前条件下没有合适主方法，方案如实不指定主方法",
                )
            )
        return violations

    primary = primary_item.method
    assessment = bundle.methods[primary]

    # --- 主方法可行性 ---
    if not assessment.feasible:
        violations.append(
            Violation(
                code="V002",
                severity="error",
                message=(
                    f"{assessment.method_cn} 的最大探测深度 {assessment.max_depth_m:g} m "
                    f"不足目标埋深 {bundle.design_depth_m:g} m，不能作为主方法"
                ),
            )
        )

    if assessment.suitability is Suitability.NOT_APPLICABLE:
        violations.append(
            Violation(
                code="V003",
                severity="error",
                message=f"{assessment.method_cn} 对{bundle.target_cn}判为不适用：{assessment.suitability_reason}",
            )
        )

    if assessment.depth_margin < 1.15:
        # 若本来就没有任何"可作主方法"的方法满足余量要求，问题不在模型的选择，
        # 而在线索本身不足；此时只提示，不强制打回，否则"所有方法都临界"的场地永远得不到方案。
        # 只把"首选/适用/受限"视为可作主方法的候选；辅助（SUPPORT）不单独定案，不算更优替换。
        adequate = [
            candidate
            for candidate in bundle.methods.values()
            if candidate.feasible
            and candidate.depth_margin >= 1.15
            and candidate.suitability
            in (Suitability.PRIMARY, Suitability.APPLICABLE, Suitability.CONSTRAINED)
        ]
        if adequate:
            violations.append(
                Violation(
                    code="V004",
                    severity="error",
                    message=(
                        f"{assessment.method_cn} 深度余量仅 {assessment.depth_margin:.2f}×，"
                        "不足 1.15×，不能承担主方法（可改用余量更大的方法）"
                    ),
                )
            )
        else:
            violations.append(
                Violation(
                    code="V004",
                    severity="warning",
                    message=(
                        f"当前埋深下没有方法满足 1.15× 余量，{assessment.method_cn} "
                        f"（{assessment.depth_margin:.2f}×）已是次优选择，建议分段设计或钻孔为主"
                    ),
                )
            )

    if assessment.suitability is Suitability.CONSTRAINED and not primary_item.mitigation:
        violations.append(
            Violation(
                code="V005",
                severity="error",
                message=(
                    f"{assessment.method_cn} 被判为受限（{assessment.suitability_reason}），"
                    "作为主方法必须给出 mitigation"
                ),
            )
        )

    if (
        primary not in bundle.recommended_primary
        and assessment.suitability is not Suitability.CONSTRAINED
    ):
        violations.append(
            Violation(
                code="V006",
                severity="warning",
                message=(
                    f"主方法 {assessment.method_cn} 与评估器推荐（"
                    f"{'、'.join(method.cn for method in bundle.recommended_primary) or '无'}）不一致，"
                    "需在 rationale 中说明理由"
                ),
            )
        )

    # --- 排除项 ---
    for item in draft.items:
        item_assessment = bundle.methods[item.method]
        if item.role is Role.EXCLUDED and item_assessment.suitability is Suitability.PRIMARY:
            violations.append(
                Violation(
                    code="V007",
                    severity="error",
                    message=f"{item.method.cn} 被判为首选方法，不能排除",
                )
            )
        if item.role is Role.PRIMARY and item.method is not primary:
            violations.append(
                Violation(
                    code="V008",
                    severity="error",
                    message=f"出现多个主方法（{item.method.cn}）",
                )
            )

    # --- 干扰与应对 ---
    if assessment.interference_notes and not primary_item.mitigation:
        violations.append(
            Violation(
                code="V009",
                severity="error",
                message=(
                    f"场地干扰（{'；'.join(assessment.interference_notes[:2])}）会影响 "
                    f"{assessment.method_cn}，主方法必须给出 mitigation"
                ),
            )
        )

    # --- 目标专用约束 ---
    if conditions.target is Target.UXO and primary not in _UXO_PRIMARY:
        violations.append(
            Violation(
                code="V010",
                severity="warning",
                message="UXO 探测的主方法应为磁法或 FDEM，当前主方法不符合常规做法",
            )
        )

    if primary is Method.DAS:
        mitigation = primary_item.mitigation or ""
        if not any(word in mitigation for word in _FIBER_KEYWORDS):
            violations.append(
                Violation(
                    code="V011",
                    severity="error",
                    message="DAS 必须依赖钻孔内光缆或既有通信光缆，主方法的 mitigation 未说明光缆来源",
                )
            )

    # --- 验证动作 ---
    verification_text = "；".join(draft.verification)
    if not any(word in verification_text for word in _VERIFICATION_KEYWORDS):
        violations.append(
            Violation(
                code="V012",
                severity="error",
                message="验证措施缺少钻孔/原位测试/试验剖面等可执行动作",
            )
        )

    # --- 风险充分性 ---
    if len(draft.risks) < 3:
        violations.append(
            Violation(
                code="V013",
                severity="warning",
                message=f"风险只列了 {len(draft.risks)} 条，建议至少 3 条（深度、干扰、多解性）",
            )
        )

    # --- 预算约束 ---
    if conditions.budget is Budget.LOW and bundle.design.cost_band == "高":
        violations.append(
            Violation(
                code="V014",
                severity="error",
                message=(
                    f"用户预算偏低，但该方案估算为高成本档（相对成本指数 "
                    f"{bundle.design.relative_cost_index:.1f}）"
                ),
            )
        )

    return violations


def has_errors(violations: list[Violation]) -> bool:
    """是否存在必须修复的问题。"""
    return any(item.severity == "error" for item in violations)
