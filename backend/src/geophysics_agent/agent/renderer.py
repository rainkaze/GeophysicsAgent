"""方案渲染器：把**已校验的结构化方案**渲染成 Markdown 正文。

为什么用代码渲染而不是让模型写正文：
- 正文里的每个数值都直接来自评估器，模型无法在最后一步"改口"；
- 正文与前端表格共享同一数据源，不会出现"表格说 A、正文说 B"；
- 渲染结果是确定性的，可做快照测试。

模型只贡献 ``rationale / mitigation / risks`` 这些**定性**文字。
"""

from __future__ import annotations

from geophysics_agent.domain.analysis import AssessmentBundle, FieldDesign
from geophysics_agent.domain.conditions import SiteConditions
from geophysics_agent.domain.enums import METHOD_ORDER, Role, Suitability
from geophysics_agent.domain.plan import SurveyPlan
from geophysics_agent.domain.schemas import Evidence

_ROLE_LABEL: dict[Role, str] = {
    Role.PRIMARY: "**主方法**",
    Role.SUPPORT: "辅助方法",
    Role.VERIFICATION: "验证方法",
    Role.EXCLUDED: "不建议采用",
}


def _cell(value: object) -> str:
    """表格单元格：转义竖线，压缩换行。"""
    return str(value).replace("|", "／").replace("\n", " ").strip()


def _num(value: float | None) -> str:
    return "—" if value is None else f"{value:g}"


def _conditions_table(conditions: SiteConditions) -> str:
    rows = [
        ("探测目标", conditions.target.cn if conditions.target else "未识别"),
        ("主要介质", conditions.medium.cn if conditions.medium else "未识别"),
        ("目标埋深", str(conditions.depth) if conditions.depth else "未识别"),
        ("地表条件", conditions.surface.value if conditions.surface else "未说明"),
        (
            "场地干扰",
            "、".join(item.cn for item in conditions.interference) or "未说明",
        ),
        ("预算约束", conditions.budget.value if conditions.budget else "未说明"),
        ("场地长度", f"{conditions.site_length_m:g} m" if conditions.site_length_m else "未说明"),
    ]
    body = "\n".join(f"| {_cell(name)} | {_cell(value)} |" for name, value in rows)
    return "| 项目 | 内容 |\n|---|---|\n" + body


def _comparison_table(plan: SurveyPlan, bundle: AssessmentBundle) -> str:
    roles = {item.method: item.role for item in plan.items}
    lines = [
        "| 方法 | 判定 | 深度余量 | 垂向分辨率 | 相对成本 | 方案角色 |",
        "|---|---|---|---|---|---|",
    ]
    for method in METHOD_ORDER:
        item = bundle.methods[method]
        resolution = (
            f"{item.vertical_resolution_m:g} m"
            if item.vertical_resolution_m is not None
            else "无垂向分辨"
        )
        role = _ROLE_LABEL.get(roles[method], "未采用") if method in roles else "未采用"
        lines.append(
            f"| {_cell(item.method_cn)} | {item.suitability.value} | {item.depth_check} | "
            f"{resolution} | {item.relative_cost} | {role} |"
        )
    return "\n".join(lines)


def _primary_section(plan: SurveyPlan, bundle: AssessmentBundle) -> list[str]:
    primary = next((item for item in plan.items if item.role is Role.PRIMARY), None)
    if primary is None:
        return [
            "### 主方法",
            "",
            "当前条件下没有可承担主方法的方案，建议先做方法试验或分段设计。",
            "",
        ]

    assessment = bundle.methods[primary.method]
    lines = [
        f"### 主方法：{assessment.method_cn}",
        "",
        f"- **选择理由**：{primary.rationale}",
        (
            f"- **深度校核**：最大探测深度 {assessment.max_depth_m:g} m，目标埋深 "
            f"{bundle.design_depth_m:g} m，{assessment.depth_check}"
        ),
        f"- **理论分辨率**：{assessment.resolution_basis}",
        f"- **物理依据**：{assessment.physics_basis}",
        f"- **布设要求**：{assessment.deployment_requirement}",
    ]
    if primary.mitigation:
        lines.append(f"- **限制应对**：{primary.mitigation}")
    else:
        lines.append("- **限制应对**：本次未提出额外应对措施")
    return lines


def _acquisition_table(bundle: AssessmentBundle, design: FieldDesign) -> str:
    method = design.primary_method
    if method is None:
        return "尚未确定主方法，暂不给出采集参数。"
    assessment = bundle.methods[method]
    lines = ["| 参数 | 取值 |", "|---|---|"]
    for key, value in assessment.acquisition.items.items():
        lines.append(f"| {_cell(key)} | {_cell(value)} |")
    return "\n".join(lines)


def _design_table(design: FieldDesign) -> str:
    if design.primary_method is None:
        return "尚未确定主方法，暂不给工作量估算。"
    rows = [
        ("主测线长度", f"{design.main_line_length_m:g} m"),
        ("测线数量", f"{design.line_count} 条（含两侧平行测线）"),
        (
            "横测线间距",
            f"{design.cross_line_spacing_m:g} m" if design.cross_line_spacing_m else "不需要",
        ),
        ("总测线长度", f"{design.total_line_km:g} km"),
        ("测点总数", f"{design.station_count} 点" if design.station_count else "按现场标定"),
        (
            "相对成本指数",
            f"{design.relative_cost_index:.1f}（{design.cost_band}成本档，GPR 每 100 m = 1）",
        ),
    ]
    body = "\n".join(f"| {_cell(name)} | {_cell(value)} |" for name, value in rows)
    return "| 项目 | 估算值 |\n|---|---|\n" + body


def _evidence_section(evidence: list[Evidence], quality: str) -> list[str]:
    if not evidence:
        return ["本次未检索到匹配的课程知识条目，以下结论不含课程出处，请谨慎使用。"]
    quality_note = {
        "strong": "相关性良好",
        "weak": "相关性偏弱，建议人工核对后再引用",
        "empty": "相关性不足，仅作线索",
    }[quality]
    lines = [f"本次检索到 {len(evidence)} 条候选证据（{quality_note}）：", ""]
    for item in evidence:
        page = f"第 {item.page} 页" if item.page else "页码未标注"
        matched = "、".join(item.matched_terms[:4]) or "—"
        lines.append(
            f"- **{item.title}**（id={item.id}）\n"
            f"  - 来源：{item.source}，{page}；状态：{item.verification_status}\n"
            f"  - 命中词：{matched}；相关度：{item.score:.2f}"
        )
    return lines


def render(
    *,
    plan: SurveyPlan,
    conditions: SiteConditions,
    bundle: AssessmentBundle,
    design: FieldDesign,
    evidence: list[Evidence],
    quality: str,
    warnings: list[str],
) -> str:
    """渲染最终 Markdown 正文。"""
    parts: list[str] = []
    target_cn = conditions.target.cn if conditions.target else "未识别目标"
    parts.append(f"# {target_cn}｜工程物探勘察方案")

    if plan.degraded:
        parts.extend(
            [
                "",
                (
                    "> ⚠️ **本方案由规则引擎直接生成**（模型不可用或未通过校验），"
                    "数值仍来自课程参数表与物理关系计算，但未经过模型的语言组织。"
                ),
            ]
        )
    parts.extend(["", f"> {plan.summary}"])

    parts.extend(["", "## 一、条件复核", "", _conditions_table(conditions)])

    parts.extend(["", "## 二、方法比选", "", _comparison_table(plan, bundle)])

    parts.extend(["", "## 三、方案要点", ""])
    parts.extend(_primary_section(plan, bundle))

    supports = [item for item in plan.items if item.role is Role.SUPPORT]
    if supports:
        parts.extend(["", "### 辅助与验证方法", ""])
        for item in supports:
            assessment = bundle.methods[item.method]
            mitigation = f"（限制应对：{item.mitigation}）" if item.mitigation else ""
            parts.append(
                f"- **{assessment.method_cn}**（余量 {assessment.depth_margin:.2f}×，"
                f"成本{assessment.relative_cost}）：{item.rationale}{mitigation}"
            )

    excluded = [item for item in plan.items if item.role is Role.EXCLUDED]
    if excluded:
        parts.extend(["", "### 不建议采用的方法", ""])
        for item in excluded:
            assessment = bundle.methods[item.method]
            if not assessment.feasible:
                label = "深度不足"
            elif assessment.suitability is Suitability.NOT_APPLICABLE:
                label = "物性不匹配"
            else:
                label = f"判定为{assessment.suitability.value}"
            parts.append(f"- **{assessment.method_cn}**（{label}）：{item.rationale}")

    parts.extend(["", "## 四、采集参数（主方法）", "", _acquisition_table(bundle, design)])

    parts.extend(["", "## 五、外业布置与工作量", "", _design_table(design)])
    if design.basis:
        parts.extend(["", "估算依据：", ""])
        parts.extend(f"- {line}" for line in design.basis)

    parts.extend(["", "## 六、风险与对策", "", "| 风险 | 影响 | 对策 |", "|---|---|---|"])
    for risk in plan.risks:
        parts.append(f"| {_cell(risk.risk)} | {_cell(risk.impact)} | {_cell(risk.response)} |")

    parts.extend(["", "## 七、验证与待补资料", "", "**验证措施**：", ""])
    parts.extend(f"- {item}" for item in plan.verification)
    if plan.missing_information:
        parts.extend(["", "**待补资料**：", ""])
        parts.extend(f"- {item}" for item in plan.missing_information)

    if warnings:
        parts.extend(["", "**系统提示**：", ""])
        parts.extend(f"- {item}" for item in warnings)

    parts.extend(["", "## 八、依据", ""])
    parts.extend(_evidence_section(evidence, quality))

    parts.extend(["", "## 九、性质说明", ""])
    parts.append(
        "本方案为课程演示级辅助建议：最大探测深度与分辨率为教学用经验估算，"
        "必须经现场试验剖面标定；物探解释具有多解性，需结合钻孔、原位测试与工程师判断。"
    )
    return "\n".join(parts).strip() + "\n"


def render_clarification(conditions: SiteConditions, questions: list[str]) -> str:
    """信息不足时的引导正文。"""
    known = []
    if conditions.target:
        known.append(f"探测目标：{conditions.target.cn}")
    if conditions.medium:
        known.append(f"主要介质：{conditions.medium.cn}")
    if conditions.depth:
        known.append(f"目标埋深：{conditions.depth}")
    known_text = "、".join(known) if known else "暂无"

    lines = [
        "# 需要补充信息",
        "",
        (
            f"目前已确认：{known_text}。还缺关键字段，无法给出可靠方案——"
            "物探方法的选择高度依赖目标物性差异与埋深，缺项时给出的方案容易变成「按名称套方法」。"
        ),
        "",
        "## 请补充",
        "",
    ]
    lines.extend(f"{index}. {question}" for index, question in enumerate(questions, start=1))
    lines.extend(
        [
            "",
            "## 补齐后我会做什么",
            "",
            "1. 用六种方法的深度-分辨率-成本评估表逐项校核；",
            "2. 按物理关系反算排列长度、电极距、天线频率等采集参数；",
            "3. 生成方案并用规则校验器自检，冲突时自动修正。",
        ]
    )
    return "\n".join(lines) + "\n"
