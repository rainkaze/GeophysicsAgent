"""评估器与物理关系测试：确认"教科书答案"级别的判定不会跑偏。"""

from __future__ import annotations

import pytest

from geophysics_agent.agent.intake import extract_conditions
from geophysics_agent.analysis import assess
from geophysics_agent.analysis.physics import (
    design_dc,
    design_gpr,
    design_surface_wave,
    gpr_velocity_m_per_ns,
)
from geophysics_agent.domain.conditions import DepthRange, SiteConditions
from geophysics_agent.domain.enums import Interference, Medium, Method, Suitability, Target


def _conditions(target: Target, medium: Medium, depth: float, **kwargs) -> SiteConditions:
    return SiteConditions(
        target=target,
        medium=medium,
        depth=DepthRange(min_m=0.0, max_m=depth),
        **kwargs,
    )


# ---------------------------------------------------------------- 主方法判定
@pytest.mark.parametrize(
    ("target", "medium", "depth", "expected"),
    [
        (Target.PLUME, Medium.CLAY, 12.0, Method.DC),
        (Target.UTILITY, Medium.FILL, 3.0, Method.GPR),
        (Target.LIQUEFACTION, Medium.SOFT_SOIL, 20.0, Method.SURFACE_WAVE),
        (Target.KARST, Medium.LIMESTONE, 15.0, Method.DC),
        (Target.AQUIFER, Medium.SAND, 30.0, Method.DC),
    ],
)
def test_recommended_primary_matches_textbook(
    target: Target, medium: Medium, depth: float, expected: Method
) -> None:
    bundle = assess(_conditions(target, medium, depth))

    assert bundle.recommended_primary == [expected]


def test_karst_gpr_is_constrained_by_insufficient_depth_margin() -> None:
    """15 m 溶洞：GPR 深度余量不足，不能被判为"首选"。"""
    bundle = assess(_conditions(Target.KARST, Medium.LIMESTONE, 15.0))

    gpr = bundle.methods[Method.GPR]
    assert gpr.feasible is True
    assert gpr.suitability is Suitability.CONSTRAINED
    assert gpr.depth_margin < 1.15


def test_gpr_is_infeasible_in_clay_at_depth() -> None:
    bundle = assess(_conditions(Target.PLUME, Medium.CLAY, 12.0))

    gpr = bundle.methods[Method.GPR]
    assert gpr.feasible is False
    assert gpr.suitability is Suitability.NOT_APPLICABLE


def test_no_method_can_cover_very_deep_target() -> None:
    bundle = assess(_conditions(Target.AQUIFER, Medium.SAND, 120.0))

    assert bundle.recommended_primary == []
    assert any("没有可行方法" in warning for warning in bundle.warnings)


def test_all_constrained_reports_no_primary_honestly() -> None:
    """UXO 在强人文干扰下：磁法/FDEM 均被降为受限，评估器不强行指定主方法。"""
    conditions = _conditions(
        Target.UXO,
        Medium.SAND,
        3.0,
        interference=[
            Interference.REBAR,
            Interference.FENCE,
            Interference.MACHINERY,
            Interference.POWERLINE,
        ],
    )
    bundle = assess(conditions)

    assert bundle.recommended_primary == []
    assert any("没有可直接推荐" in warning for warning in bundle.warnings)


def test_refraction_is_primary_for_site_investigation() -> None:
    """工程勘察：地震折射是基岩面/覆盖层厚度的经典主方法之一。"""
    bundle = assess(_conditions(Target.SITE_INVESTIGATION, Medium.BEDROCK, 20.0))

    assert bundle.methods[Method.REFRACTION].suitability is Suitability.PRIMARY
    assert bundle.methods[Method.REFRACTION].feasible


def test_tem_covers_deep_aquifer() -> None:
    """含水层：TEM 是深部低阻体的经典方法，应可行且适用。"""
    bundle = assess(_conditions(Target.AQUIFER, Medium.SAND, 40.0))

    assert bundle.methods[Method.TEM].feasible
    assert bundle.methods[Method.TEM].suitability is Suitability.APPLICABLE


# ---------------------------------------------------------------- 干扰判定
def test_severe_interference_downgrades_magnetic_in_urban_site() -> None:
    conditions = extract_conditions(
        "城市道路填土场地需要探测地下管线，埋深 2 m，地表有钢筋混凝土地面，附近有 10 kV 电力线。"
    )
    assert conditions.interference, "测试前提：应识别出干扰"
    bundle = assess(conditions)

    assert bundle.methods[Method.MAGNETIC].suitability is Suitability.CONSTRAINED


def test_mitigable_interference_does_not_block_primary() -> None:
    """地形起伏只是要求做地形改正，不应把 DC 从"适用"降级。"""
    conditions = _conditions(
        Target.KARST,
        Medium.LIMESTONE,
        15.0,
    ).model_copy(update={"interference": [extract_conditions("地形起伏较大").interference[0]]})
    bundle = assess(conditions)

    assert bundle.methods[Method.DC].suitability is Suitability.APPLICABLE
    assert bundle.methods[Method.DC].interference_notes


# ---------------------------------------------------------------- 采集参数
def test_dc_array_length_covers_target_depth() -> None:
    design = design_dc(15.0)

    assert design.array_length_m >= 4 * 15.0 * 0.9
    assert design.spacing_m > 0
    assert design.resolution_m == pytest.approx(2.2, abs=0.2)


def test_surface_wave_array_length_uses_2_5_factor() -> None:
    design = design_surface_wave(20.0)

    assert design.array_length_m >= 2.5 * 20.0 * 0.9


def test_gpr_velocity_and_resolution_are_physical() -> None:
    clay = gpr_velocity_m_per_ns(Medium.CLAY)
    sand = gpr_velocity_m_per_ns(Medium.SAND)
    assert clay < sand  # 介电常数越大，速度越低

    design = design_gpr(Medium.LIMESTONE, 15.0, base_depth_m=16.0)
    assert design.antenna_mhz <= 100.0
    assert 0.1 < design.resolution_m < 1.5
    assert design.window_ns > 0


def test_gpr_utility_uses_high_frequency_for_resolution() -> None:
    """浅层管线是小目标，GPR 应选较高频率（≥250 MHz）而非 100 MHz。"""
    bundle = assess(_conditions(Target.UTILITY, Medium.FILL, 3.0))

    frequency = bundle.methods[Method.GPR].acquisition.items["天线中心频率"]
    assert frequency.startswith(("250", "500"))


# ---------------------------------------------------------------- 外业设计
def test_design_has_traceable_basis_and_cost_band() -> None:
    bundle = assess(_conditions(Target.KARST, Medium.LIMESTONE, 15.0))

    design = bundle.design
    assert design.total_line_km > 0
    assert design.station_count is not None and design.station_count > 0
    assert design.cost_band in {"低", "中", "高"}
    assert len(design.basis) >= 3


def test_assess_rejects_incomplete_conditions() -> None:
    with pytest.raises(ValueError, match="不完整"):
        assess(SiteConditions())
