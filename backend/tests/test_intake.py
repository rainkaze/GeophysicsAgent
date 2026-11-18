"""条件抽取测试：覆盖范围、否定语境、歧义目标与多轮合并。"""

from __future__ import annotations

from geophysics_agent.agent.intake import build_questions, extract_conditions
from geophysics_agent.domain.conditions import DepthRange, SiteConditions
from geophysics_agent.domain.enums import Interference, Medium, Surface, Target


def test_extracts_core_fields_from_scenario() -> None:
    conditions = extract_conditions("场地为厚层黏土，目标埋深约 5~12 m，需要追踪地下水污染羽。")

    assert conditions.target is Target.PLUME
    assert conditions.medium is Medium.CLAY
    assert conditions.depth == DepthRange(min_m=5.0, max_m=12.0)


def test_depth_range_takes_upper_bound_as_design_depth() -> None:
    conditions = extract_conditions("灰岩场地，需要探测溶洞，埋深 4~15 m。")

    assert conditions.depth is not None
    assert conditions.depth.design_depth_m == 15.0


def test_negated_interference_is_ignored() -> None:
    """ "无重要金属设施"不能识别成金属干扰。"""
    conditions = extract_conditions("场地地表为农田，无重要金属设施，但周边有灌溉井。")

    assert Interference.REBAR not in conditions.interference


def test_positive_interference_is_detected() -> None:
    conditions = extract_conditions("地表有钢筋混凝土地面，附近还有 10 kV 电力线。")

    assert Interference.REBAR in conditions.interference
    assert Interference.POWERLINE in conditions.interference


def test_ambiguous_target_prefers_plume_over_aquifer() -> None:
    """ "地下水污染羽"应识别为污染羽，而不是含水层。"""
    conditions = extract_conditions("需要追踪地下水污染羽的运移通道。")

    assert conditions.target is Target.PLUME


def test_site_investigation_target_from_bedrock_cover() -> None:
    """ "覆盖层厚度/基岩面"应识别为工程勘察。"""
    conditions = extract_conditions("基岩场地，需要查明覆盖层厚度与基岩面埋深。")

    assert conditions.target is Target.SITE_INVESTIGATION
    assert conditions.medium is Medium.BEDROCK


def test_surface_detection() -> None:
    assert extract_conditions("地表为碎石覆盖，地形起伏较大").surface is Surface.GRAVEL
    assert extract_conditions("道路和小区绿化带内查找管线").surface is Surface.GRASS


def test_missing_critical_fields_and_questions() -> None:
    conditions = extract_conditions("我想做一次物探看看地下有什么东西。")

    assert not conditions.is_complete()
    assert set(conditions.missing_critical()) == {"探测目标", "主要介质", "目标埋深"}
    questions = build_questions(conditions)
    assert len(questions) == 3


def test_merge_keeps_previous_values() -> None:
    """多轮：第二轮只改埋深，其余字段沿用上一轮。"""
    previous = SiteConditions(
        target=Target.AQUIFER,
        medium=Medium.SAND,
        depth=DepthRange(min_m=30.0, max_m=30.0),
    )
    update = extract_conditions("那如果埋深改成 60 m，方案要怎么调整？")
    merged = previous.merge(update)

    assert merged.target is Target.AQUIFER
    assert merged.medium is Medium.SAND
    assert merged.depth is not None
    assert merged.depth.design_depth_m == 60.0


def test_water_level_is_not_treated_as_target_depth() -> None:
    conditions = extract_conditions("地下水位约 1 m，需要获取 0~20 m 浅层横波速度结构。")

    assert conditions.depth is not None
    assert conditions.depth.design_depth_m == 20.0
