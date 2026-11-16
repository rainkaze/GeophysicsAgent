"""方法评估器：把"目标 + 介质 + 埋深 + 干扰"变成六种方法的确定性评估。

这是整个 agent 的**事实来源**。大模型只能引用这里的数字，不能自己编。
判定顺序严格固定，便于解释与测试：

1. 深度可行性（最大深度 / 设计埋深）
2. 物性适用性（基础矩阵 + 目标专用理由）
3. 深度余量是否充足（余量 <1.15 时不得判为"首选/适用"）
4. 介质限制（强限制，直接降为"受限"）
5. 场地干扰（区分"严重干扰"与"可通过施工措施缓解的干扰"）

其中第 5 步的区分很关键：钢筋网会真的毁掉 GPR 数据，而地形起伏只是要求做地形改正。
若把两者同等降级，任何山区场地都会得出"没有首选方法"的错误结论。
"""

from __future__ import annotations

from geophysics_agent.analysis.catalog import (
    INTERFERENCE_CONSTRAINTS,
    METHOD_META,
    SEVERE_INTERFERENCE,
)
from geophysics_agent.analysis.design import build_design
from geophysics_agent.analysis.physics import (
    design_das,
    design_dc,
    design_fdem,
    design_gpr,
    design_magnetic,
    design_surface_wave,
)
from geophysics_agent.analysis.tables import (
    BASE_MAX_DEPTH,
    BASE_SUITABILITY,
    INAPPLICABLE_REASON,
    MEDIUM_CONSTRAINTS,
    TARGET_CONTRAST,
    TARGET_DEPTH_FACTOR,
    TARGET_EXTRA_LIMITATIONS,
    TARGET_NOTES,
)
from geophysics_agent.domain.analysis import (
    AcquisitionParams,
    AssessmentBundle,
    MethodAssessment,
)
from geophysics_agent.domain.conditions import SiteConditions
from geophysics_agent.domain.enums import (
    METHOD_ORDER,
    Medium,
    Method,
    Suitability,
    Target,
)

#: 深度余量阈值：≥1.6 为满足，≥1.15 为临界，≥1.0 为余量不足（不可作主方法）
MARGIN_SATISFY = 1.6
MARGIN_CRITICAL = 1.15
#: 判定为"可行"的最低余量
MARGIN_FEASIBLE = 1.0

_BASE_REASON: dict[Suitability, str] = {
    Suitability.PRIMARY: "物性差异直接、深度与分辨率满足目标要求，适合作为主方法",
    Suitability.APPLICABLE: "对本目标有效且深度满足，可作为辅助或交叉验证方法",
    Suitability.SUPPORT: "可提供间接约束，通常作为辅助手段，不单独定案",
    Suitability.CONSTRAINED: "存在明确限制，需调整配置或改换方法",
}


def max_depth_of(method: Method, medium: Medium, target: Target) -> float:
    """经验最大探测深度 = 介质基准值 × 目标尺寸修正。"""
    base = BASE_MAX_DEPTH[method][medium]
    return round(base * TARGET_DEPTH_FACTOR[method][target], 1)


def depth_check(ratio: float, max_depth: float, depth: float) -> str:
    """把深度余量翻译成可读文本。"""
    if ratio >= MARGIN_SATISFY:
        return f"满足（余量 {ratio:.1f}×）"
    if ratio >= MARGIN_CRITICAL:
        return f"临界（余量 {ratio:.1f}×）"
    if ratio >= MARGIN_FEASIBLE:
        return f"余量不足（{ratio:.2f}×）"
    return f"超限（{depth:g} m > {max_depth:g} m）"


def _split_constraints(
    conditions: SiteConditions, method: Method, ratio: float
) -> tuple[list[str], list[str]]:
    """返回（会导致降级的限制，仅需在方案中说明的限制）。"""
    blocking: list[str] = []
    notes: list[str] = []
    medium = conditions.medium
    assert medium is not None, "评估前必须保证介质已知"

    if ratio < MARGIN_CRITICAL:
        blocking.append(f"深度余量仅 {ratio:.2f}×，属理论上限，实际施工中易受衰减与噪声影响")

    medium_note = MEDIUM_CONSTRAINTS.get(method, {}).get(medium)
    if medium_note:
        blocking.append(medium_note)

    severe = SEVERE_INTERFERENCE.get(method, frozenset())
    for interference in conditions.interference:
        note = INTERFERENCE_CONSTRAINTS.get(method, {}).get(interference)
        if not note:
            continue
        notes.append(f"{interference.cn}：{note}")
        if interference in severe:
            blocking.append(f"{interference.cn}：{note}")

    return blocking, notes


def _suitability(
    conditions: SiteConditions,
    method: Method,
    ratio: float,
    feasible: bool,
    blocking: list[str],
) -> tuple[Suitability, str]:
    """按固定顺序给出适用性与理由。"""
    target = conditions.target
    medium = conditions.medium
    depth_range = conditions.depth
    assert target is not None and medium is not None and depth_range is not None
    base = BASE_SUITABILITY[target][method]

    if not feasible:
        return (
            Suitability.NOT_APPLICABLE,
            (
                f"最大探测深度 {max_depth_of(method, medium, target):g} m "
                f"< 目标埋深 {depth_range.design_depth_m:g} m，无法可靠覆盖目标"
            ),
        )

    if base is Suitability.NOT_APPLICABLE:
        specific = INAPPLICABLE_REASON.get((method, target))
        return (
            Suitability.NOT_APPLICABLE,
            specific
            or f"该方法不测量{target.cn}所依赖的物性（{TARGET_CONTRAST[target]}），不宜采用",
        )

    if blocking and base in (Suitability.PRIMARY, Suitability.APPLICABLE):
        return Suitability.CONSTRAINED, "；".join(blocking)
    if blocking and base is Suitability.SUPPORT:
        return Suitability.SUPPORT, "；".join([_BASE_REASON[base], *blocking])

    return base, _BASE_REASON[base]


def _acquisition_and_resolution(
    conditions: SiteConditions, method: Method, max_depth: float
) -> tuple[AcquisitionParams, float | None, str, float | None, float | None]:
    """返回（采集参数、分辨率、分辨率依据、点距、排列长度）。"""
    medium = conditions.medium
    depth_range = conditions.depth
    assert medium is not None and depth_range is not None
    depth = depth_range.design_depth_m

    if method is Method.GPR:
        gpr = design_gpr(medium, depth, max_depth)
        return (
            AcquisitionParams(
                items={
                    "天线中心频率": f"{gpr.antenna_mhz:g} MHz",
                    "记录时窗": f"{gpr.window_ns:g} ns",
                    "点距": f"{gpr.point_spacing_m:g} m",
                    "测线方向": "垂直目标走向，跨越已知异常布设",
                }
            ),
            gpr.resolution_m,
            gpr.note,
            gpr.point_spacing_m,
            None,
        )

    if method is Method.DC:
        dc = design_dc(depth)
        return (
            AcquisitionParams(
                items={
                    "电极排列": "温纳（普查）+ 偶极-偶极（异常加密）",
                    "电极距": f"{dc.spacing_m:g} m",
                    "排列长度": f"{dc.array_length_m:g} m（{dc.channels} 道）",
                    "接地要求": "高阻/碎石地表需浇水或换位，逐点记录接地电阻",
                }
            ),
            dc.resolution_m,
            dc.note,
            dc.spacing_m,
            dc.array_length_m,
        )

    if method is Method.SURFACE_WAVE:
        sw = design_surface_wave(depth)
        return (
            AcquisitionParams(
                items={
                    "道间距": f"{sw.spacing_m:g} m",
                    "排列长度": f"{sw.array_length_m:g} m（{sw.channels} 道）",
                    "震源": "锤击或落重，多次叠加",
                    "环境": "避开强振动时段，记录背景噪声",
                }
            ),
            sw.resolution_m,
            sw.note,
            sw.spacing_m,
            sw.array_length_m,
        )

    if method is Method.MAGNETIC:
        mag = design_magnetic(depth)
        return (
            AcquisitionParams(
                items={
                    "线距": f"{mag.line_spacing_m:g} m",
                    "点距": f"{mag.station_spacing_m:g} m",
                    "高度": "探头离地约 0.5 m，必要时做多高度测量",
                    "校正": "日变改正 + 静态改正，避开车辆与铁质物体",
                }
            ),
            mag.resolution_m,
            mag.note,
            mag.station_spacing_m,
            None,
        )

    if method is Method.FDEM:
        fdem_design = design_fdem(depth)
        return (
            AcquisitionParams(
                items={
                    "线圈距": f"{fdem_design.line_spacing_m:g} m",
                    "频段": fdem_design.note.split("；")[0],
                    "点距": f"{fdem_design.station_spacing_m:g} m",
                    "姿态": "保持线圈姿态与离地高度一致，先做零点校正",
                }
            ),
            fdem_design.resolution_m,
            fdem_design.note,
            fdem_design.station_spacing_m,
            None,
        )

    das = design_das(depth)
    return (
        AcquisitionParams(
            items={
                "通道间距": f"{das.channel_spacing_m:g} m",
                "光缆长度": f"≥{das.borehole_depth_m:g} m（钻孔或既有通信光缆）",
                "解调": "需专业解调仪与相位解缠处理",
            }
        ),
        das.resolution_m,
        das.note,
        das.channel_spacing_m,
        None,
    )


def _limitations(conditions: SiteConditions, method: Method, extra_notes: list[str]) -> list[str]:
    """组合目标专用、介质、干扰与通用限制，去重后截断。"""
    target = conditions.target
    medium = conditions.medium
    assert target is not None and medium is not None
    items: list[str] = []
    extra = TARGET_EXTRA_LIMITATIONS.get(target, {}).get(method)
    if extra:
        items.append(extra)
    medium_note = MEDIUM_CONSTRAINTS.get(method, {}).get(medium)
    if medium_note:
        items.append(medium_note)
    items.extend(extra_notes)
    items.extend(METHOD_META[method].base_limitations)

    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:6]


def _state_tier(suitability: Suitability) -> int:
    """当前判定状态：可用优先，受限其次，仅可辅助最后。"""
    return {
        Suitability.APPLICABLE: 0,
        Suitability.CONSTRAINED: 1,
        Suitability.SUPPORT: 2,
    }.get(suitability, 3)


def _promotion_tier(method: Method, target: Target) -> int:
    """基础物性适配度：越接近"首选"，越优先被指定为主方法。"""
    base = BASE_SUITABILITY[target][method]
    return {
        Suitability.PRIMARY: 0,
        Suitability.APPLICABLE: 1,
        Suitability.SUPPORT: 2,
    }.get(base, 3)


def _promote_primary(
    methods: dict[Method, MethodAssessment], target: Target, warnings: list[str]
) -> list[Method]:
    """当没有任何方法判为"首选"时，按"当前判定 → 基础适配度 → 深度余量"指定主方法。

    只按深度余量排序会把 DAS 这类"深度大但成本高、依赖钻孔"的方法抬成主方法；
    只按基础适配度排序又会把"已判为受限"的方法抬回来（例如 15 m 溶洞里的 GPR）。
    因此先看当前判定状态，再看基础适配度，最后比余量。
    """
    primary = [m for m in METHOD_ORDER if methods[m].suitability is Suitability.PRIMARY]
    if primary:
        return primary

    candidates = [
        method
        for method in METHOD_ORDER
        if methods[method].feasible
        and methods[method].suitability
        in (Suitability.APPLICABLE, Suitability.SUPPORT, Suitability.CONSTRAINED)
    ]
    if not candidates:
        warnings.append("当前条件下没有可行方法，建议改用钻探为主或分段设计")
        return []

    candidates.sort(
        key=lambda method: (
            _state_tier(methods[method].suitability),
            _promotion_tier(method, target),
            -methods[method].depth_margin,
        )
    )
    best = candidates[0]
    warnings.append(
        f"当前埋深下没有方法判为“首选”，按判定状态与深度余量改以 "
        f"{methods[best].method_cn}（余量 {methods[best].depth_margin:.2f}×）为主方法"
    )
    return [best]


def assess(conditions: SiteConditions) -> AssessmentBundle:
    """对六种方法做完整评估，并给出推荐主辅方法与外业设计。

    ``conditions`` 必须包含 target / medium / depth，否则抛 ``ValueError``。
    """
    if not conditions.is_complete():
        raise ValueError(f"场地条件不完整，缺少：{'、'.join(conditions.missing_critical())}")

    target = conditions.target
    medium = conditions.medium
    depth_range = conditions.depth
    assert target is not None and medium is not None and depth_range is not None
    depth = depth_range.design_depth_m

    methods: dict[Method, MethodAssessment] = {}
    warnings: list[str] = []

    for method in METHOD_ORDER:
        max_depth = max_depth_of(method, medium, target)
        ratio = round(max_depth / depth, 3)
        feasible = ratio >= MARGIN_FEASIBLE
        blocking, notes = _split_constraints(conditions, method, ratio)
        suitability, reason = _suitability(conditions, method, ratio, feasible, blocking)
        with_assessment = _acquisition_and_resolution(conditions, method, max_depth)
        params, resolution, resolution_basis, spacing, array_length = with_assessment

        meta = METHOD_META[method]
        methods[method] = MethodAssessment(
            method=method,
            method_cn=method.cn,
            max_depth_m=max_depth,
            depth_margin=ratio,
            depth_check=depth_check(ratio, max_depth, depth),
            feasible=feasible,
            suitability=suitability,
            suitability_reason=reason,
            vertical_resolution_m=resolution,
            resolution_basis=resolution_basis,
            station_spacing_m=spacing,
            array_length_m=array_length,
            relative_cost=meta.relative_cost,
            cost_index=meta.cost_index_per_100m,
            acquisition=params,
            physics_basis=meta.physics_basis,
            deployment_requirement=meta.deployment_requirement,
            limitations=_limitations(conditions, method, blocking + notes),
            interference_notes=notes,
        )

    primary = _promote_primary(methods, target, warnings)
    support = [
        method
        for method in METHOD_ORDER
        if method not in primary
        and methods[method].suitability
        in (Suitability.APPLICABLE, Suitability.SUPPORT, Suitability.CONSTRAINED)
    ]
    infeasible = [method for method in METHOD_ORDER if not methods[method].feasible]

    for method in infeasible:
        warnings.append(
            f"{method.cn} 最大探测深度 {methods[method].max_depth_m:g} m "
            f"< 目标埋深 {depth:g} m，无法覆盖目标"
        )
    if methods[Method.DAS].feasible and methods[Method.DAS].suitability.is_usable:
        warnings.append("DAS 需要钻孔内光缆或既有通信光缆，场地不具备时不能作为独立方法")
    if target in (Target.PLUME, Target.AQUIFER):
        warnings.append("磁法对污染羽/含水层没有直接物性响应，只能用于排查铁磁干扰或管线")
    if medium is Medium.FILL:
        warnings.append("填土中常含建筑垃圾与钢筋，GPR 与 DC 都可能出现强干扰，需先做试验剖面")

    design_method = primary[0] if primary else None
    design = build_design(
        design_method,
        methods[design_method] if design_method else None,
        site_length_m=conditions.site_length_m,
        depth_m=depth,
        target=target,
    )

    return AssessmentBundle(
        target_cn=target.cn,
        medium_cn=medium.cn,
        design_depth_m=depth,
        depth_range=str(depth_range),
        methods=methods,
        recommended_primary=primary,
        recommended_support=support,
        infeasible=infeasible,
        design=design,
        warnings=warnings,
        target_contrast=TARGET_CONTRAST[target],
        target_note=TARGET_NOTES[target],
    )
