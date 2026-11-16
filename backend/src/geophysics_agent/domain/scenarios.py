"""内置 4 个标准测试场景（课程汇报 Demo 样例）。

每个场景都包含：
- query        给大模型看的自然语言描述
- target_name  兜底查表用的规范目标名
- medium       规范介质名
- target_depth 校核埋深（范围取上限）
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    sid: str
    title: str
    query: str
    target_name: str
    medium: str
    target_depth: float
    depth_range: str


SCENARIOS: list[Scenario] = [
    Scenario(
        sid="1",
        title="厚黏土场地追踪地下水污染羽",
        query=(
            "场地为厚层黏土（饱水、低阻），需要追踪地下水污染羽的分布范围与运移通道，"
            "目标埋深约 5~12 m。场地地表为农田，无重要金属设施，但周边有灌溉井和民房。"
            "请给出物探勘察方案。"
        ),
        target_name="污染羽",
        medium="黏土",
        target_depth=12.0,
        depth_range="5~12 m",
    ),
    Scenario(
        sid="2",
        title="城市浅层查找金属/混凝土管线",
        query=(
            "城市浅层场地，需要在道路和小区绿化带内查找地下金属与混凝土管线，埋深 1~3 m。"
            "地表有钢筋混凝土地面、围栏、路灯和车辆等人文干扰，附近还有 10 kV 电力线。"
            "请给出物探勘察方案。"
        ),
        target_name="地下管线",
        medium="填土",
        target_depth=3.0,
        depth_range="1~3 m",
    ),
    Scenario(
        sid="3",
        title="软土场地评估地震液化风险",
        query=(
            "滨海软土场地，地下水位约 1 m，需要评估地震液化风险，获取 0~20 m 浅层横波速度结构。"
            "场地为开阔空地，允许布置较长排列，附近有轻微交通振动。请给出物探勘察方案。"
        ),
        target_name="土层液化",
        medium="软土",
        target_depth=20.0,
        depth_range="0~20 m",
    ),
    Scenario(
        sid="4",
        title="山区路基探测灰岩溶洞",
        query=(
            "山区路基工程，围岩为灰岩，需要探测地下溶洞与空洞，埋深 4~15 m。"
            "地表为碎石覆盖、地形起伏较大，附近有公路施工机械作业。请给出物探勘察方案。"
        ),
        target_name="溶洞",
        medium="灰岩",
        target_depth=15.0,
        depth_range="4~15 m",
    ),
]


def get_scenario(sid: str) -> Scenario:
    """按编号取场景，找不到时给出友好错误。"""
    for scenario in SCENARIOS:
        if scenario.sid == sid:
            return scenario
    valid = "、".join(s.sid for s in SCENARIOS)
    raise ValueError(f"没有编号为 '{sid}' 的场景，可选：{valid}")
