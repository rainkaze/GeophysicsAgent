"""课程知识表：别名、物性对比、深度经验值、适用性矩阵与介质/目标专用说明。

数值来源为《工程地球物理导论》课程量与教材量级整理，属**教学用经验区间**：
最大探测深度指"最佳配置、低噪声条件下的上限"，不是某台仪器的标称指标，
现场必须用试验剖面标定，不能直接当作设计值。
"""

from __future__ import annotations

from geophysics_agent.domain.enums import Medium, Method, Suitability, Target

# ============================================================
# 1. 别名与优先级
# ============================================================
# 目标别名按优先级匹配（先命中者胜），避免"地下水污染羽"被识别成含水层。
TARGET_PRIORITY: tuple[Target, ...] = (
    Target.UTILITY,
    Target.PLUME,
    Target.KARST,
    Target.UXO,
    Target.LIQUEFACTION,
    Target.AQUIFER,
    Target.SITE_INVESTIGATION,
)

TARGET_ALIASES: dict[Target, tuple[str, ...]] = {
    Target.UTILITY: ("管线", "管道", "pipe", "电缆", "混凝土管", "地下管"),
    Target.PLUME: ("污染", "羽", "plume", "contaminant", "污染物"),
    Target.KARST: ("溶洞", "空洞", "岩溶", "karst", "cavity", "void", "土洞", "脱空"),
    Target.UXO: ("uxo", "未爆", "炸弹", "弹药", "爆炸物"),
    Target.LIQUEFACTION: ("液化", "liquefaction"),
    Target.AQUIFER: ("含水层", "地下水", "aquifer"),
    Target.SITE_INVESTIGATION: (
        "勘察",
        "site investigation",
        "geotechnical",
        "地层分层",
        "覆盖层",
        "基岩面",
        "地基",
    ),
}

MEDIUM_PRIORITY: tuple[Medium, ...] = (
    Medium.LIMESTONE,
    Medium.BEDROCK,
    Medium.SOFT_SOIL,
    Medium.CLAY,
    Medium.SILT,
    Medium.SAND,
    Medium.FILL,
)

MEDIUM_ALIASES: dict[Medium, tuple[str, ...]] = {
    Medium.LIMESTONE: ("灰岩", "石灰岩", "limestone", "碳酸盐岩"),
    Medium.BEDROCK: ("基岩", "bedrock", "岩石", "强风化"),
    Medium.SOFT_SOIL: ("软土", "淤泥", "soft soil", "mud", "软黏土"),
    Medium.CLAY: ("黏土", "粘土", "clay", "粉质黏土"),
    Medium.SILT: ("粉土", "silt", "粉砂"),
    Medium.SAND: ("砂土", "砂层", "sand", "砂砾", "砾砂"),
    Medium.FILL: ("填土", "回填", "杂填", "素填", "fill"),
}

# ============================================================
# 2. 物性对比与解释要点
# ============================================================
TARGET_CONTRAST: dict[Target, str] = {
    Target.PLUME: "电阻率/电导率差异（TDS、离子浓度、NAPL 影响）",
    Target.UTILITY: "金属的高电导率/高磁化率，或管壁与土的介电、波阻抗差异",
    Target.KARST: "空洞与围岩的电阻率、介电常数、波速差异",
    Target.AQUIFER: "含水层与隔水层的电阻率差异、Vs 差异",
    Target.UXO: "铁磁体的磁化率异常与金属高电导率",
    Target.LIQUEFACTION: "液化砂层与上覆层的 Vs、密度差异",
    Target.SITE_INVESTIGATION: "地层波速、电阻率、介电差异",
}

TARGET_NOTES: dict[Target, str] = {
    Target.PLUME: "电阻率异常由 TDS、NAPL 与黏土含量共同控制，异常≠污染物浓度，需钻孔取样验证。",
    Target.UTILITY: "金属管线可用磁法/电磁感应，非金属管线主要靠 GPR 的介电差异。",
    Target.KARST: "溶洞可为空洞（高阻）或黏土充填（低阻），电性响应相反，需地质资料约束。",
    Target.AQUIFER: "低阻异常可能是含水层，也可能是黏土层，需结合岩性与钻孔水位。",
    Target.UXO: "异常幅度随距离三次方衰减，探测概率随埋深/目标尺寸下降，必须按安全规程开挖验证。",
    Target.LIQUEFACTION: "液化判别需要 Vs 或 SPT/CPT，加上地下水位与砂层分布，物探只提供速度结构。",
    Target.SITE_INVESTIGATION: "物探提供间接参数，需钻孔与原位测试标定后才能用于设计。",
}

#: GPR 小目标所需的最小垂向分辨率（m）：管线/UXO 尺寸小，必须选更高频率才能分辨。
#: 其余大目标（溶洞/含水层/分层等）不设此约束，仍按深度覆盖选频。
GPR_TARGET_RESOLUTION_M: dict[Target, float] = {
    Target.UTILITY: 0.15,
    Target.UXO: 0.05,
}

# ============================================================
# 3. 最大探测深度（m）：最佳配置下的经验上限
# ============================================================
BASE_MAX_DEPTH: dict[Method, dict[Medium, float]] = {
    Method.GPR: {
        Medium.CLAY: 3.0,
        Medium.SOFT_SOIL: 2.0,
        Medium.SILT: 6.0,
        Medium.SAND: 15.0,
        Medium.FILL: 8.0,
        Medium.LIMESTONE: 20.0,
        Medium.BEDROCK: 15.0,
    },
    Method.DC: {
        Medium.CLAY: 25.0,
        Medium.SOFT_SOIL: 20.0,
        Medium.SILT: 30.0,
        Medium.SAND: 35.0,
        Medium.FILL: 25.0,
        Medium.LIMESTONE: 40.0,
        Medium.BEDROCK: 40.0,
    },
    Method.SURFACE_WAVE: {
        Medium.CLAY: 25.0,
        Medium.SOFT_SOIL: 30.0,
        Medium.SILT: 30.0,
        Medium.SAND: 35.0,
        Medium.FILL: 20.0,
        Medium.LIMESTONE: 40.0,
        Medium.BEDROCK: 50.0,
    },
    Method.MAGNETIC: {
        Medium.CLAY: 5.0,
        Medium.SOFT_SOIL: 5.0,
        Medium.SILT: 5.0,
        Medium.SAND: 5.0,
        Medium.FILL: 5.0,
        Medium.LIMESTONE: 5.0,
        Medium.BEDROCK: 4.0,
    },
    Method.FDEM: {
        Medium.CLAY: 12.0,
        Medium.SOFT_SOIL: 8.0,
        Medium.SILT: 15.0,
        Medium.SAND: 20.0,
        Medium.FILL: 10.0,
        Medium.LIMESTONE: 25.0,
        Medium.BEDROCK: 20.0,
    },
    Method.REFRACTION: {
        Medium.CLAY: 25.0,
        Medium.SOFT_SOIL: 30.0,
        Medium.SILT: 30.0,
        Medium.SAND: 35.0,
        Medium.FILL: 20.0,
        Medium.LIMESTONE: 40.0,
        Medium.BEDROCK: 50.0,
    },
    Method.TEM: {
        Medium.CLAY: 30.0,
        Medium.SOFT_SOIL: 40.0,
        Medium.SILT: 50.0,
        Medium.SAND: 60.0,
        Medium.FILL: 30.0,
        Medium.LIMESTONE: 60.0,
        Medium.BEDROCK: 60.0,
    },
    Method.DAS: {medium: 50.0 for medium in Medium},
}

# 目标尺寸/可识别性修正：系数 >1 表示目标尺度大于方法的分辨单元。
# 注意：不允许用 >1.2 的系数去"放大"方法能力，那会把工具结论推到不可靠的方向。
TARGET_DEPTH_FACTOR: dict[Method, dict[Target, float]] = {
    Method.GPR: {
        Target.PLUME: 0.8,
        Target.UTILITY: 0.6,
        Target.KARST: 0.8,
        Target.AQUIFER: 0.6,
        Target.UXO: 0.8,
        Target.LIQUEFACTION: 0.5,
        Target.SITE_INVESTIGATION: 1.0,
    },
    Method.DC: {
        Target.PLUME: 1.0,
        Target.UTILITY: 0.8,
        Target.KARST: 1.0,
        Target.AQUIFER: 1.0,
        Target.UXO: 0.5,
        Target.LIQUEFACTION: 1.0,
        Target.SITE_INVESTIGATION: 1.0,
    },
    Method.SURFACE_WAVE: {
        Target.PLUME: 0.9,
        Target.UTILITY: 0.3,
        Target.KARST: 1.0,
        Target.AQUIFER: 1.0,
        Target.UXO: 0.3,
        Target.LIQUEFACTION: 1.0,
        Target.SITE_INVESTIGATION: 1.0,
    },
    Method.MAGNETIC: {
        Target.PLUME: 0.5,
        Target.UTILITY: 1.0,
        Target.KARST: 0.6,
        Target.AQUIFER: 0.5,
        Target.UXO: 0.6,
        Target.LIQUEFACTION: 0.5,
        Target.SITE_INVESTIGATION: 1.0,
    },
    Method.FDEM: {
        Target.PLUME: 1.0,
        Target.UTILITY: 0.8,
        Target.KARST: 1.2,
        Target.AQUIFER: 1.2,
        Target.UXO: 0.6,
        Target.LIQUEFACTION: 1.0,
        Target.SITE_INVESTIGATION: 1.0,
    },
    Method.REFRACTION: {
        Target.PLUME: 0.5,
        Target.UTILITY: 0.3,
        Target.KARST: 0.8,
        Target.AQUIFER: 1.0,
        Target.UXO: 0.3,
        Target.LIQUEFACTION: 1.0,
        Target.SITE_INVESTIGATION: 1.0,
    },
    Method.TEM: {
        Target.PLUME: 1.0,
        Target.UTILITY: 0.8,
        Target.KARST: 1.2,
        Target.AQUIFER: 1.2,
        Target.UXO: 0.6,
        Target.LIQUEFACTION: 1.0,
        Target.SITE_INVESTIGATION: 1.0,
    },
    Method.DAS: {target: 1.0 for target in Target},
}

# ============================================================
# 4. 适用性基础矩阵（与深度无关；深度不足时会被判为不适用）
# ============================================================
BASE_SUITABILITY: dict[Target, dict[Method, Suitability]] = {
    Target.PLUME: {
        Method.GPR: Suitability.SUPPORT,
        Method.DC: Suitability.PRIMARY,
        Method.SURFACE_WAVE: Suitability.SUPPORT,
        Method.REFRACTION: Suitability.SUPPORT,
        Method.MAGNETIC: Suitability.NOT_APPLICABLE,
        Method.FDEM: Suitability.APPLICABLE,
        Method.TEM: Suitability.APPLICABLE,
        Method.DAS: Suitability.SUPPORT,
    },
    Target.UTILITY: {
        Method.GPR: Suitability.PRIMARY,
        Method.DC: Suitability.SUPPORT,
        Method.SURFACE_WAVE: Suitability.NOT_APPLICABLE,
        Method.REFRACTION: Suitability.NOT_APPLICABLE,
        Method.MAGNETIC: Suitability.APPLICABLE,
        Method.FDEM: Suitability.APPLICABLE,
        Method.TEM: Suitability.SUPPORT,
        Method.DAS: Suitability.NOT_APPLICABLE,
    },
    Target.KARST: {
        Method.GPR: Suitability.PRIMARY,
        Method.DC: Suitability.APPLICABLE,
        Method.SURFACE_WAVE: Suitability.APPLICABLE,
        Method.REFRACTION: Suitability.APPLICABLE,
        Method.MAGNETIC: Suitability.NOT_APPLICABLE,
        Method.FDEM: Suitability.SUPPORT,
        Method.TEM: Suitability.SUPPORT,
        Method.DAS: Suitability.NOT_APPLICABLE,
    },
    Target.AQUIFER: {
        Method.GPR: Suitability.SUPPORT,
        Method.DC: Suitability.PRIMARY,
        Method.SURFACE_WAVE: Suitability.APPLICABLE,
        Method.REFRACTION: Suitability.APPLICABLE,
        Method.MAGNETIC: Suitability.NOT_APPLICABLE,
        Method.FDEM: Suitability.APPLICABLE,
        Method.TEM: Suitability.APPLICABLE,
        Method.DAS: Suitability.SUPPORT,
    },
    Target.UXO: {
        Method.GPR: Suitability.SUPPORT,
        Method.DC: Suitability.NOT_APPLICABLE,
        Method.SURFACE_WAVE: Suitability.NOT_APPLICABLE,
        Method.REFRACTION: Suitability.NOT_APPLICABLE,
        Method.MAGNETIC: Suitability.PRIMARY,
        Method.FDEM: Suitability.PRIMARY,
        Method.TEM: Suitability.SUPPORT,
        Method.DAS: Suitability.NOT_APPLICABLE,
    },
    Target.LIQUEFACTION: {
        Method.GPR: Suitability.SUPPORT,
        Method.DC: Suitability.SUPPORT,
        Method.SURFACE_WAVE: Suitability.PRIMARY,
        Method.REFRACTION: Suitability.APPLICABLE,
        Method.MAGNETIC: Suitability.NOT_APPLICABLE,
        Method.FDEM: Suitability.SUPPORT,
        Method.TEM: Suitability.SUPPORT,
        Method.DAS: Suitability.APPLICABLE,
    },
    Target.SITE_INVESTIGATION: {
        Method.GPR: Suitability.APPLICABLE,
        Method.DC: Suitability.APPLICABLE,
        Method.SURFACE_WAVE: Suitability.PRIMARY,
        Method.REFRACTION: Suitability.PRIMARY,
        Method.MAGNETIC: Suitability.SUPPORT,
        Method.FDEM: Suitability.SUPPORT,
        Method.TEM: Suitability.SUPPORT,
        Method.DAS: Suitability.SUPPORT,
    },
}

# 介质对方法的附加限制：命中则把"首选/适用"降为"受限"。
MEDIUM_CONSTRAINTS: dict[Method, dict[Medium, str]] = {
    Method.GPR: {
        Medium.CLAY: "湿黏土电导率可达约 100 mS/m，电磁波强衰减，有效深度通常仅 1–3 m",
        Medium.SOFT_SOIL: "软土饱水、电导率高，GPR 衰减大，有效深度通常不足 2 m",
    },
    Method.FDEM: {
        Medium.CLAY: "低阻黏土覆盖层屏蔽深部二次场，需增大线圈距或降低频率",
        Medium.SOFT_SOIL: "软土高导覆盖层屏蔽深部响应，深部异常弱",
    },
    Method.MAGNETIC: {
        Medium.BEDROCK: "基岩若含磁铁矿会抬升背景、产生干扰异常",
    },
}

# 目标与方法物性不匹配时的专用说明（比通用理由更具体）。
INAPPLICABLE_REASON: dict[tuple[Method, Target], str] = {
    (Method.MAGNETIC, Target.PLUME): "磁法只对铁磁性（铁、钢）目标有效，污染羽不产生磁异常",
    (Method.MAGNETIC, Target.AQUIFER): "磁法只对铁磁性目标有效，含水层不产生磁异常",
    (Method.MAGNETIC, Target.LIQUEFACTION): "磁法只对铁磁性目标有效，液化砂层不产生磁异常",
    (Method.MAGNETIC, Target.KARST): "磁法只对铁磁性目标有效，溶洞不产生磁异常",
    (Method.DC, Target.UXO): "直流电阻率对小型金属目标响应弱、分辨率不足，不适合 UXO 探测",
    (Method.SURFACE_WAVE, Target.UXO): "面波分辨率低（米级），无法识别小型 UXO",
    (Method.SURFACE_WAVE, Target.UTILITY): "面波横向分辨率低，难以识别小口径管线",
    (
        Method.DAS,
        Target.UTILITY,
    ): "DAS 只测量沿光纤的应变/振动，不能直接探测管线，且需钻孔或既有光缆",
    (Method.DAS, Target.KARST): "DAS 只测量沿光纤的应变/振动，不能直接探测溶洞",
    (Method.DAS, Target.UXO): "DAS 只测量沿光纤的应变/振动，不能直接探测 UXO",
    (Method.REFRACTION, Target.UTILITY): "地震折射垂向分辨率低（米级），无法识别小口径管线",
    (Method.REFRACTION, Target.UXO): "地震折射无法识别小型 UXO",
}

# 目标专用补充限制（追加到方法限制列表前面）。
TARGET_EXTRA_LIMITATIONS: dict[Target, dict[Method, str]] = {
    Target.PLUME: {
        Method.DC: "只能给出电性异常，不能识别污染物种类与浓度，需钻孔取样与地球化学分析验证",
        Method.FDEM: "电导率异常受黏土含量与矿化度共同控制，需多频/多装置约束",
    },
    Target.UTILITY: {
        Method.GPR: "非金属管线反射弱，管径小、充水或埋深大于 3 m 时可能漏检",
        Method.MAGNETIC: "混凝土/PVC 管线无磁响应；金属管线的磁异常与钢筋、围栏难以区分",
    },
    Target.KARST: {
        Method.DC: "空洞（高阻）与黏土充填（低阻）响应相反，存在等值性",
        Method.GPR: "充水、充泥溶洞衰减明显增大，深部信号弱",
    },
    Target.AQUIFER: {
        Method.DC: "低阻异常可能是含水层，也可能是黏土层，需钻孔水位与岩性约束",
    },
    Target.UXO: {
        Method.MAGNETIC: "探测概率随埋深、目标尺寸和方位变化，不能保证 100% 检出",
        Method.FDEM: "铁质碎片与土壤电导率变化会产生大量假异常",
    },
    Target.LIQUEFACTION: {
        Method.SURFACE_WAVE: "Vs 与液化势为经验关系，需 SPT/CPT 标定",
        Method.DAS: "需钻孔或既有光缆，且只能提供 Vs，不能直接判定液化",
    },
}

DISCLAIMER = (
    "本结果为课程演示级辅助建议。最大探测深度为教学用经验上限，"
    "实际受场地噪声、目标尺寸与含水状态影响，必须经现场试验剖面标定；"
    "物探解释具有多解性，需结合钻孔、原位测试及工程师判断。"
)
