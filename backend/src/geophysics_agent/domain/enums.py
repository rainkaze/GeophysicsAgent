"""领域枚举：物探方法、探测目标、介质、适用性、方案角色与场地条件。

枚举值统一使用 ASCII 小写代码（便于 JSON 传输与日志检索），
中文展示名通过 ``cn`` 属性获取，避免在业务代码里散落硬编码汉字。
"""

from __future__ import annotations

from enum import Enum


class Method(str, Enum):
    """课程覆盖的六种工程物探方法。"""

    GPR = "gpr"
    DC = "dc"
    SURFACE_WAVE = "surface_wave"
    MAGNETIC = "magnetic"
    FDEM = "fdem"
    DAS = "das"

    @property
    def cn(self) -> str:
        return _METHOD_CN[self]

    @property
    def short_cn(self) -> str:
        return _METHOD_SHORT_CN[self]


_METHOD_CN: dict[Method, str] = {
    Method.GPR: "探地雷达（GPR）",
    Method.DC: "直流电阻率（DC/ERT）",
    Method.SURFACE_WAVE: "面波地震（MASW）",
    Method.MAGNETIC: "磁法勘探",
    Method.FDEM: "频域电磁（FDEM）",
    Method.DAS: "分布式光纤声学（DAS）",
}

_METHOD_SHORT_CN: dict[Method, str] = {
    Method.GPR: "GPR",
    Method.DC: "DC/ERT",
    Method.SURFACE_WAVE: "面波",
    Method.MAGNETIC: "磁法",
    Method.FDEM: "FDEM",
    Method.DAS: "DAS",
}

METHOD_ORDER: tuple[Method, ...] = (
    Method.GPR,
    Method.DC,
    Method.SURFACE_WAVE,
    Method.MAGNETIC,
    Method.FDEM,
    Method.DAS,
)


class Target(str, Enum):
    """典型探测目标。"""

    PLUME = "plume"
    UTILITY = "utility"
    KARST = "karst"
    AQUIFER = "aquifer"
    UXO = "uxo"
    LIQUEFACTION = "liquefaction"
    SITE_INVESTIGATION = "site_investigation"

    @property
    def cn(self) -> str:
        return _TARGET_CN[self]


_TARGET_CN: dict[Target, str] = {
    Target.PLUME: "污染羽",
    Target.UTILITY: "地下管线",
    Target.KARST: "溶洞与空洞",
    Target.AQUIFER: "含水层",
    Target.UXO: "UXO 未爆物",
    Target.LIQUEFACTION: "土层液化",
    Target.SITE_INVESTIGATION: "工程勘察",
}


class Medium(str, Enum):
    """目标所处的规范介质类型。"""

    CLAY = "clay"
    SILT = "silt"
    SAND = "sand"
    FILL = "fill"
    LIMESTONE = "limestone"
    BEDROCK = "bedrock"
    SOFT_SOIL = "soft_soil"

    @property
    def cn(self) -> str:
        return _MEDIUM_CN[self]


_MEDIUM_CN: dict[Medium, str] = {
    Medium.CLAY: "黏土",
    Medium.SILT: "粉土",
    Medium.SAND: "砂土",
    Medium.FILL: "填土",
    Medium.LIMESTONE: "灰岩",
    Medium.BEDROCK: "基岩",
    Medium.SOFT_SOIL: "软土",
}


class Suitability(str, Enum):
    """单一方法对某目标在该埋深下的适用性判定。"""

    PRIMARY = "首选"
    APPLICABLE = "适用"
    SUPPORT = "辅助"
    CONSTRAINED = "受限"
    NOT_APPLICABLE = "不适用"

    @property
    def is_usable(self) -> bool:
        return self is not Suitability.NOT_APPLICABLE


class Role(str, Enum):
    """方法在最终勘察方案中承担的角色。"""

    PRIMARY = "主方法"
    SUPPORT = "辅助方法"
    VERIFICATION = "验证方法"
    EXCLUDED = "不建议采用"


class Surface(str, Enum):
    """地表覆盖条件，直接影响耦合、接地与布设成本。"""

    PAVED = "硬化路面"
    GRASS = "农田草地"
    GRAVEL = "碎石覆盖"
    WATER = "水域"
    UNKNOWN = "未说明"


class Interference(str, Enum):
    """常见人文/环境干扰类型。"""

    REBAR = "钢筋与金属构筑物"
    POWERLINE = "电力线/高压线"
    TRAFFIC = "交通车辆"
    MACHINERY = "施工机械"
    FENCE = "围栏铁栅"
    VIBRATION = "持续振动"
    TERRAIN = "地形起伏"

    @property
    def cn(self) -> str:
        return self.value


class Budget(str, Enum):
    """用户给出的预算约束等级。"""

    LOW = "偏低"
    MEDIUM = "中等"
    HIGH = "充足"
