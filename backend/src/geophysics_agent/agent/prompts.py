"""提示词模板：模型只做"选择题 + 写理由"，不做数值计算。

三条硬约束写在系统提示里，并由校验器在后端强制：
1. 数值只能引用评估表；
2. 只能使用给定的方法代码与角色；
3. 必须恰好一个主方法，且不选的方法也要给理由。
"""

from __future__ import annotations

from geophysics_agent.domain.analysis import AssessmentBundle
from geophysics_agent.domain.conditions import SiteConditions
from geophysics_agent.domain.enums import METHOD_ORDER
from geophysics_agent.domain.plan import PlanDraft, Violation
from geophysics_agent.domain.schemas import Evidence

SYSTEM_PROMPT = """你是工程物探勘察方案的决策助手，服务对象是《工程地球物理导论》课程的项目汇报。

你的任务：在给定条件下，从固定的八种方法中选择勘察方案的角色分配，并写出可核查的理由。

必须遵守的规则：
1. 只能使用【评估表】中已有的数值。禁止自行计算、换算或编造任何深度、分辨率、成本、间距、排列长度。
2. 方法代码只能取：gpr、dc、surface_wave、refraction、magnetic、fdem、tem、das；必须覆盖全部八种方法、每种只出现一次并给出一个角色。
3. 角色只能取：主方法 / 辅助方法 / 验证方法 / 不建议采用。若评估表给出了"推荐主方法"，则必须恰好有一个"主方法"；若评估表显示没有推荐主方法（八种方法均受限或不适用），不要强行指定主方法——items 全部填"不建议采用"，并在 summary 里如实说明没有合适主方法、建议扩展方法或钻探为主。
4. 主方法原则上取评估表中的"推荐主方法"。如果场地条件（干扰、地表、预算、目标性质）让你改选其他方法，必须在 rationale 中说明是哪一条条件改变了判断，并给出 mitigation。
5. 被判为"不适用"的方法只能放进"不建议采用"，并引用评估表给出的理由或该限制。
6. rationale 中的课程依据只能用【证据】里列出的条目 id，写成「（见 ERT-001）」的形式，不得虚构 id。
7. risks 给 3–5 条，每条必须能对应到评估表中的限制、干扰或目标专用提示。
8. verification 至少 1 条，必须包含钻孔/原位测试/试验剖面这类可执行的验证动作。
9. 输出**只能**是一个 JSON 对象，不要代码块、不要解释、不要多余文字。

JSON 结构：
{
  "summary": "一到两句话的方案结论",
  "items": [
    {"method": "dc", "role": "主方法", "rationale": "为什么由它承担主方法（引用数值或证据 id）", "mitigation": "针对场地限制的应对措施，可为 null"}
  ],
  "risks": [{"risk": "风险", "impact": "影响", "response": "对策"}],
  "verification": ["钻孔验证：每个异常至少 1 个钻孔"],
  "missing_information": ["还需补充的资料"]
}"""


def _format_methods(bundle: AssessmentBundle) -> str:
    """把八种方法的评估压缩成可读表格文本。"""
    lines = [
        "方法代码 | 方法 | 最大深度m | 深度余量 | 深度校核 | 适用性 | 垂向分辨率m | 成本 | 关键限制",
        "---|---|---|---|---|---|---|---|---",
    ]
    for method in METHOD_ORDER:
        item = bundle.methods[method]
        resolution = (
            f"{item.vertical_resolution_m:g}"
            if item.vertical_resolution_m is not None
            else "无垂向分辨"
        )
        limit = item.limitations[0] if item.limitations else "-"
        lines.append(
            f"{method.value} | {item.method_cn} | {item.max_depth_m:g} | {item.depth_margin:.2f}× | "
            f"{item.depth_check} | {item.suitability.value} | {resolution} | {item.relative_cost} | {limit}"
        )
    return "\n".join(lines)


def _format_evidence(evidence: list[Evidence]) -> str:
    if not evidence:
        return "（本次未检索到课程知识条目）"
    return "\n".join(
        f"- id={item.id}｜{item.title}｜来源={item.source}｜页码={item.page or '未标注'}"
        f"｜状态={item.verification_status}"
        for item in evidence
    )


def _format_conditions(conditions: SiteConditions) -> str:
    return "\n".join(
        [
            f"- 探测目标：{conditions.target.cn if conditions.target else '未知'}",
            f"- 主要介质：{conditions.medium.cn if conditions.medium else '未知'}",
            f"- 目标埋深：{conditions.depth if conditions.depth else '未知'}",
            f"- 地表条件：{conditions.surface.value if conditions.surface else '未说明'}",
            "- 场地干扰：" + ("、".join(item.cn for item in conditions.interference) or "未说明"),
            f"- 预算约束：{conditions.budget.value if conditions.budget else '未说明'}",
            f"- 场地长度：{conditions.site_length_m or '未说明'}",
        ]
    )


def build_plan_user(
    *,
    message: str,
    conditions: SiteConditions,
    bundle: AssessmentBundle,
    evidence: list[Evidence],
) -> str:
    """构造方案生成请求。"""
    primary = "、".join(method.value for method in bundle.recommended_primary) or "无"
    support = "、".join(method.value for method in bundle.recommended_support) or "无"
    infeasible = "、".join(method.value for method in bundle.infeasible) or "无"

    design = bundle.design
    design_text = "\n".join(f"- {line}" for line in design.basis) or "- 未生成"

    return f"""## 用户场景描述
{message}

## 已解析的场地条件
{_format_conditions(conditions)}

## 评估表（唯一事实来源，数值不得改动）
{_format_methods(bundle)}

## 计算器结论
- 推荐主方法：{primary}
- 可作为辅助：{support}
- 深度不可行：{infeasible}
- 目标物性对比：{bundle.target_contrast}
- 目标解释提示：{bundle.target_note}
- 系统提示：{("；".join(bundle.warnings)) or "无"}

## 外业设计草案（可引用，不得改动数值）
{design_text}

## 证据（只能引用这些 id）
{_format_evidence(evidence)}

请按系统提示的 JSON 结构输出方案。方法代码、角色取值必须与规定一致。"""


def build_repair_user(
    *,
    conditions: SiteConditions,
    bundle: AssessmentBundle,
    draft: PlanDraft,
    violations: list[Violation],
) -> str:
    """构造修复请求：把校验器发现的问题原样回灌。"""
    problems = "\n".join(f"- [{item.code}] {item.message}" for item in violations)
    current = "\n".join(
        f"- {item.method.value}：{item.role.value}｜{item.rationale}" for item in draft.items
    )
    return f"""你上一次输出的方案没有通过校验，请只修正被指出的问题，其余内容保持不变。

## 场地条件
{_format_conditions(conditions)}

## 评估表
{_format_methods(bundle)}

## 你上一次的方案
{current}

## 必须修正的问题
{problems}

请重新输出完整的 JSON 方案（结构不变），并确保不再违反上述任一条。"""
