"""外业布置与工作量估算：把"方法 + 场地长度"变成可核对的测线与成本。

全部为教学用估算：测线数量、线距、工作量与相对成本指数都给出推导依据，
便于在方案正文中逐条追溯，也便于教师质疑时定位到具体假设。
"""

from __future__ import annotations

from geophysics_agent.analysis.catalog import METHOD_META
from geophysics_agent.domain.analysis import FieldDesign, MethodAssessment
from geophysics_agent.domain.enums import Method, Target

#: 默认场地可布设长度（m）；用户未给出时使用
DEFAULT_SITE_LENGTH_M = 200.0
#: 主测线两侧的平行测线数
FLANK_LINES = 2
#: 需要网格式控制的目标（线状目标更依赖横测线）
CROSS_LINE_TARGETS: tuple[Target, ...] = (Target.KARST, Target.UTILITY, Target.SITE_INVESTIGATION)
CROSS_LINE_SPACING_M = 30.0
CROSS_LINE_LENGTH_M = 60.0
#: 相对成本分档阈值（成本指数 = 单价指数 × 百 m 数）
COST_BAND_LOW = 12.0
COST_BAND_MEDIUM = 35.0


def build_design(
    method: Method | None,
    assessment: MethodAssessment | None,
    *,
    site_length_m: float | None = None,
    depth_m: float,
    target: Target | None = None,
) -> FieldDesign:
    """基于主方法、场地长度与目标类型生成外业布置与工作量。"""
    if method is None or assessment is None:
        return FieldDesign(basis=["尚未确定主方法，暂不给出外业布置"])

    main_length = float(site_length_m or DEFAULT_SITE_LENGTH_M)
    line_count = 1 + FLANK_LINES
    basis: list[str] = [
        f"主测线沿勘查对象走向布置，长度按场地可布设长度取 {main_length:g} m",
        f"主测线两侧各布 1 条平行测线，合计 {line_count} 条",
    ]

    cross_spacing: float | None = None
    total_length = main_length * line_count
    if target in CROSS_LINE_TARGETS:
        cross_spacing = CROSS_LINE_SPACING_M
        cross_count = max(1, round(main_length / cross_spacing))
        total_length += cross_count * CROSS_LINE_LENGTH_M
        basis.append(
            f"{target.cn}需要平面控制，每 {cross_spacing:g} m 加 1 条 {CROSS_LINE_LENGTH_M:g} m 横测线，"
            f"共 {cross_count} 条"
        )

    station_count: int | None = None
    spacing = assessment.station_spacing_m
    if spacing:
        station_count = round(total_length / spacing)
        basis.append(f"按点距/电极距 {spacing:g} m 计，测点总数约 {station_count} 点")

    cost_index = METHOD_META[method].cost_index_per_100m * total_length / 100.0
    if cost_index <= COST_BAND_LOW:
        band = "低"
    elif cost_index <= COST_BAND_MEDIUM:
        band = "中"
    else:
        band = "高"
    basis.append(
        f"相对成本指数 = {METHOD_META[method].cost_index_per_100m:g}（每 100 m，GPR=1）"
        f" × {total_length / 100.0:.1f} 个百 m = {cost_index:.1f}，属{band}成本档"
    )

    return FieldDesign(
        primary_method=method,
        main_line_length_m=round(main_length, 1),
        line_count=line_count,
        cross_line_spacing_m=cross_spacing,
        total_line_km=round(total_length / 1000.0, 3),
        station_count=station_count,
        relative_cost_index=round(cost_index, 1),
        cost_band=band,
        basis=basis,
    )
