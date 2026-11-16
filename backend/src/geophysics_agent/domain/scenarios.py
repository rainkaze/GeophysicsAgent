"""内置标准测试场景（课堂演示用）。

每个场景是一段可直接粘贴的自然语言描述，配合 ``analysis`` 与 ``agent`` 使用，
同时通过 ``GET /api/v1/scenarios`` 暴露给前端，避免示例散落在前后端两处。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Scenario(BaseModel):
    """一个可一键填入的演示场景。"""

    model_config = ConfigDict(frozen=True)

    sid: str
    title: str
    query: str
    target_cn: str
    medium_cn: str
    depth_range: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        sid="1",
        title="厚黏土场地追踪地下水污染羽",
        query=(
            "场地为厚层黏土（饱水、低阻），需要追踪地下水污染羽的分布范围与运移通道，"
            "目标埋深约 5~12 m。场地地表为农田，无重要金属设施，但周边有灌溉井和民房。"
            "请给出物探勘察方案。"
        ),
        target_cn="污染羽",
        medium_cn="黏土",
        depth_range="5~12 m",
    ),
    Scenario(
        sid="2",
        title="城市浅层查找金属/混凝土管线",
        query=(
            "城市浅层场地，地层以填土为主，需要在道路和小区绿化带内查找地下金属与混凝土管线，埋深 1~3 m。"
            "地表有钢筋混凝土地面、围栏、路灯和车辆等人文干扰，附近还有 10 kV 电力线。"
            "请给出物探勘察方案。"
        ),
        target_cn="地下管线",
        medium_cn="填土",
        depth_range="1~3 m",
    ),
    Scenario(
        sid="3",
        title="软土场地评估地震液化风险",
        query=(
            "滨海软土场地，地下水位约 1 m，需要评估地震液化风险，获取 0~20 m 浅层横波速度结构。"
            "场地为开阔空地，允许布置较长排列，附近有轻微交通振动。请给出物探勘察方案。"
        ),
        target_cn="土层液化",
        medium_cn="软土",
        depth_range="0~20 m",
    ),
    Scenario(
        sid="4",
        title="山区路基探测灰岩溶洞",
        query=(
            "山区路基工程，围岩为灰岩，需要探测地下溶洞与空洞，埋深 4~15 m。"
            "地表为碎石覆盖、地形起伏较大，附近有公路施工机械作业。请给出物探勘察方案。"
        ),
        target_cn="溶洞与空洞",
        medium_cn="灰岩",
        depth_range="4~15 m",
    ),
)


def get_scenario(sid: str) -> Scenario:
    """按编号取场景；找不到时抛出 ``KeyError``（由路由层转 404）。"""
    for scenario in SCENARIOS:
        if scenario.sid == sid:
            return scenario
    raise KeyError(sid)
