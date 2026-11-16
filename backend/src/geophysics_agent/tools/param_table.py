"""物探参数查表数据与判定规则（课程知识整理）。

这张表是工具 geophysical_param_lookup 的"知识底座"：
- 六种方法在不同介质中的最大探测深度（经验值，最佳配置下的上限）
- 纵向分辨率、相对成本、关键限制（严格对应课程知识点）
- 针对目标/介质/埋深的适用性判定

注意：数值是课程量级下的教学用经验区间，不是某台仪器的标称指标；
现场必须通过试验剖面标定，不能直接当作设计值。
"""

from __future__ import annotations

import re
from typing import Any

# ============================================================
# 1. 基础常量
# ============================================================
METHOD_ORDER: tuple[str, ...] = ("GPR", "DC", "面波", "磁法", "FDEM", "DAS")

METHOD_CN: dict[str, str] = {
    "GPR": "探地雷达（GPR）",
    "DC": "直流电阻率（DC/ERT）",
    "面波": "面波地震（MASW）",
    "磁法": "磁法勘探",
    "FDEM": "频域电磁（FDEM）",
    "DAS": "分布式光纤声学（DAS）",
}

# 介质别名 -> 规范介质名
MEDIUM_ALIASES: dict[str, list[str]] = {
    "灰岩": ["灰岩", "石灰岩", "limestone", "碳酸盐岩"],
    "基岩": ["基岩", "bedrock", "岩石", "强风化"],
    "软土": ["软土", "淤泥", "淤泥质", "soft soil", "mud"],
    "黏土": ["黏土", "粘土", "clay", "粉质黏土"],
    "粉土": ["粉土", "silt", "粉砂"],
    "砂土": ["砂土", "砂层", "sand", "砂砾", "砾砂"],
    "填土": ["填土", "回填", "杂填", "素填", "fill"],
}

# 目标别名 -> 规范目标名（顺序有意义：先匹配"地下管线"，再匹配"空洞"）
TARGET_ALIASES: dict[str, list[str]] = {
    "地下管线": ["管线", "管道", "pipe", "电缆", "混凝土管"],
    "污染羽": ["污染", "羽", "plume", "contaminant"],
    "溶洞": ["溶洞", "空洞", "岩溶", "karst", "cavity", "void"],
    "含水层": ["含水层", "地下水", "aquifer"],
    "UXO": ["uxo", "未爆", "炸弹", "弹药", "爆炸物"],
    "土层液化": ["液化", "liquefaction"],
    "工程勘察": ["勘察", "site investigation", "geotechnical"],
}

# 目标的主要物性差异（用于向大模型解释"为什么这个方法行/不行"）
TARGET_CONTRAST: dict[str, str] = {
    "污染羽": "电阻率/电导率差异（TDS、离子浓度、NAPL 影响）",
    "地下管线": "金属的高电导率/高磁化率，或管壁与土的介电、波阻抗差异",
    "溶洞": "空洞与围岩的电阻率、介电常数、波速差异",
    "含水层": "含水层与隔水层的电阻率差异、Vs 差异",
    "UXO": "铁磁体的磁化率异常与金属高电导率",
    "土层液化": "液化砂层与上覆层的 Vs、密度差异",
    "工程勘察": "地层波速、电阻率、介电差异",
}

TARGET_NOTES: dict[str, str] = {
    "污染羽": "电阻率异常由 TDS、NAPL 与黏土含量共同控制，异常≠污染物浓度，需钻孔取样验证。",
    "地下管线": "金属管线可用磁法/电磁感应，非金属管线主要靠 GPR 的介电差异。",
    "溶洞": "溶洞可为空洞（高阻）或黏土充填（低阻），电性响应相反，需地质资料约束。",
    "含水层": "低阻异常可能是含水层，也可能是黏土层，需结合岩性与钻孔水位。",
    "UXO": "异常幅度随距离三次方衰减，探测概率随埋深/目标尺寸下降，必须按安全规程开挖验证。",
    "土层液化": "液化判别需要 Vs 或 SPT/CPT，加上地下水位与砂层分布，物探只提供速度结构。",
    "工程勘察": "物探提供间接参数，需钻孔与原位测试标定后才能用于设计。",
}

# ============================================================
# 2. 最大探测深度（m）：最佳配置下的经验上限
# ============================================================
BASE_MAX_DEPTH: dict[str, dict[str, float]] = {
    # GPR：受介电常数与电导率控制；黏土/软土强衰减，干燥灰岩穿透最好
    "GPR": {
        "黏土": 3.0,
        "软土": 2.0,
        "粉土": 6.0,
        "砂土": 15.0,
        "填土": 8.0,
        "灰岩": 20.0,
        "基岩": 15.0,
    },
    # DC/ERT：受排列长度控制，约 0.2–0.3 倍排列长度
    "DC": {
        "黏土": 25.0,
        "软土": 20.0,
        "粉土": 30.0,
        "砂土": 35.0,
        "填土": 25.0,
        "灰岩": 40.0,
        "基岩": 40.0,
    },
    # 面波：排列长度约 2–3 倍最大深度
    "面波": {
        "黏土": 25.0,
        "软土": 30.0,
        "粉土": 30.0,
        "砂土": 35.0,
        "填土": 20.0,
        "灰岩": 40.0,
        "基岩": 50.0,
    },
    # 磁法：与目标磁性质量、埋深有关，此处按小型铁磁目标（数 kg）估算
    "磁法": {
        "黏土": 5.0,
        "软土": 5.0,
        "粉土": 5.0,
        "砂土": 5.0,
        "填土": 5.0,
        "灰岩": 5.0,
        "基岩": 4.0,
    },
    # FDEM：EM31 约 6 m，EM34 大线圈可更深；黏土低阻覆盖层会屏蔽
    "FDEM": {
        "黏土": 12.0,
        "软土": 8.0,
        "粉土": 15.0,
        "砂土": 20.0,
        "填土": 10.0,
        "灰岩": 25.0,
        "基岩": 20.0,
    },
    # DAS：深度由光缆布设决定（钻孔内约 50 m），此处按常规钻孔深度
    "DAS": {m: 50.0 for m in MEDIUM_ALIASES},
}

# 目标尺寸/可识别性修正：小目标需要更近的观测距离，实际有效深度打折
TARGET_DEPTH_FACTOR: dict[str, dict[str, float]] = {
    "GPR": {
        "污染羽": 0.8,
        "地下管线": 0.6,
        "溶洞": 1.2,
        "含水层": 0.6,
        "UXO": 0.8,
        "土层液化": 0.5,
        "工程勘察": 1.0,
    },
    "DC": {
        "污染羽": 1.0,
        "地下管线": 0.8,
        "溶洞": 1.0,
        "含水层": 1.0,
        "UXO": 0.5,
        "土层液化": 1.0,
        "工程勘察": 1.0,
    },
    "面波": {
        "污染羽": 0.9,
        "地下管线": 0.3,
        "溶洞": 1.0,
        "含水层": 1.0,
        "UXO": 0.3,
        "土层液化": 1.0,
        "工程勘察": 1.0,
    },
    "磁法": {
        "污染羽": 0.5,
        "地下管线": 1.4,
        "溶洞": 0.6,
        "含水层": 0.5,
        "UXO": 0.6,
        "土层液化": 0.5,
        "工程勘察": 1.0,
    },
    "FDEM": {
        "污染羽": 1.0,
        "地下管线": 0.8,
        "溶洞": 1.2,
        "含水层": 1.5,
        "UXO": 0.6,
        "土层液化": 1.0,
        "工程勘察": 1.0,
    },
    "DAS": {t: 1.0 for t in TARGET_ALIASES},
}

# ============================================================
# 3. 适用性基础矩阵（与深度无关，深度不满足时会被降为"不适用"）
# ============================================================
BASE_SUITABILITY: dict[str, dict[str, str]] = {
    "污染羽": {
        "GPR": "辅助",
        "DC": "首选",
        "面波": "辅助",
        "磁法": "不适用",
        "FDEM": "适用",
        "DAS": "辅助",
    },
    "地下管线": {
        "GPR": "首选",
        "DC": "辅助",
        "面波": "不适用",
        "磁法": "适用",
        "FDEM": "适用",
        "DAS": "不适用",
    },
    "溶洞": {
        "GPR": "首选",
        "DC": "适用",
        "面波": "适用",
        "磁法": "不适用",
        "FDEM": "辅助",
        "DAS": "不适用",
    },
    "含水层": {
        "GPR": "辅助",
        "DC": "首选",
        "面波": "适用",
        "磁法": "不适用",
        "FDEM": "适用",
        "DAS": "辅助",
    },
    "UXO": {
        "GPR": "辅助",
        "DC": "不适用",
        "面波": "不适用",
        "磁法": "首选",
        "FDEM": "首选",
        "DAS": "不适用",
    },
    "土层液化": {
        "GPR": "辅助",
        "DC": "辅助",
        "面波": "首选",
        "磁法": "不适用",
        "FDEM": "辅助",
        "DAS": "适用",
    },
    "工程勘察": {
        "GPR": "适用",
        "DC": "适用",
        "面波": "首选",
        "磁法": "辅助",
        "FDEM": "辅助",
        "DAS": "辅助",
    },
}

# 介质对方法的附加限制：命中则把"首选/适用"降为"受限"
MEDIUM_CONSTRAINTS: dict[str, dict[str, str]] = {
    "GPR": {
        "黏土": "湿黏土电导率可达约 100 mS/m，电磁波强衰减，有效深度通常仅 1–3 m",
        "软土": "软土饱水、电导率高，GPR 衰减大，有效深度通常不足 2 m",
    },
    "FDEM": {
        "黏土": "低阻黏土覆盖层屏蔽深部二次场，需增大线圈距或降低频率",
        "软土": "软土高导覆盖层屏蔽深部响应，深部异常弱",
    },
    "磁法": {
        "基岩": "基岩若含磁铁矿会抬升背景、产生干扰异常",
    },
}

# 目标与方法物性不匹配时的专用说明（比通用理由更具体）
INAPPLICABLE_REASON: dict[tuple[str, str], str] = {
    ("磁法", "污染羽"): "磁法只对铁磁性（铁、钢）目标有效，污染羽不产生磁异常",
    ("磁法", "含水层"): "磁法只对铁磁性目标有效，含水层不产生磁异常",
    ("磁法", "土层液化"): "磁法只对铁磁性目标有效，液化砂层不产生磁异常",
    ("磁法", "溶洞"): "磁法只对铁磁性目标有效，溶洞不产生磁异常",
    ("DC", "UXO"): "直流电阻率对小型金属目标响应弱、分辨率不足，不适合 UXO 探测",
    ("面波", "UXO"): "面波分辨率低（米级），无法识别小型 UXO",
    ("面波", "地下管线"): "面波横向分辨率低，难以识别小口径管线",
    ("DAS", "地下管线"): "DAS 只测量沿光纤的应变/振动，不能直接探测管线，且需钻孔或既有光缆",
    ("DAS", "溶洞"): "DAS 只测量沿光纤的应变/振动，不能直接探测溶洞",
    ("DAS", "UXO"): "DAS 只测量沿光纤的应变/振动，不能直接探测 UXO",
}

# ============================================================
# 4. 分辨率、成本、限制、物理原理
# ============================================================
RESOLUTION: dict[str, str] = {
    "GPR": "约 0.05–0.5 m（λ/4，随天线频率与介电常数变化；250 MHz 时约 0.1–0.3 m）",
    "DC": "约 0.1–0.25 倍目标埋深（薄层分辨差，存在等值性）",
    "面波": "约 0.1–0.3 倍目标埋深（分层 Vs，界面不锐利）",
    "磁法": "无垂向分辨能力（仅平面定位，深度需多高度/梯度反演）",
    "FDEM": "约 0.3–0.5 倍勘探深度（扩散场，垂向分辨低）",
    "DAS": "约 1 m（通道间距），沿光纤连续分布",
}

RELATIVE_COST: dict[str, str] = {
    "GPR": "低",
    "DC": "中",
    "面波": "低",
    "磁法": "低",
    "FDEM": "中",
    "DAS": "高",
}

BASE_LIMITATIONS: dict[str, list[str]] = {
    "GPR": [
        "高电导介质（湿黏土、含水层、盐渍土）中电磁波强衰减，有效深度骤减",
        "钢筋网、围栏、金属管线产生强反射并屏蔽下方目标",
        "介电常数未知时深度换算误差可达 10%–20%",
        "天线频率越高分辨率越高、穿透越浅，需权衡",
    ],
    "DC": [
        "反演非唯一性（等值性），薄层与低阻围岩中的目标难以分辨",
        "金属管线、围栏、电力接地使电流畸变，产生假异常",
        "高阻基岩、混凝土地面接地困难，需浇水或改变电极位置",
        "探测深度受排列长度限制，深部横向分辨率下降",
    ],
    "面波": [
        "1D 水平层状假设，横向分辨率低，复杂地形/陡界面不可靠",
        "城市交通与机械振动降低信噪比",
        "软土低速层导致速度反转，需多模式反演",
        "空洞、管线尺寸小于波长时响应弱",
    ],
    "磁法": [
        "仅对铁磁性（铁、钢）目标有效，对非铁磁目标没有直接响应",
        "钢筋、围栏、车辆、电力线的人文干扰强",
        "无垂向分辨能力，深度需多高度或梯度反演",
        "异常幅度随距离三次方衰减，小目标随埋深迅速失效",
    ],
    "FDEM": [
        "高导覆盖层（黏土、盐渍土、含水层）屏蔽深部响应",
        "金属管线、围栏强响应压制小目标",
        "扩散场垂向分辨率低，层状解释多解",
        "响应受线圈姿态与背景电导率影响，需相对测量",
    ],
    "DAS": [
        "需要钻孔内光缆或既有通信光缆，场地条件限制大",
        "仅测量沿光纤一维应变/振动，空间覆盖受光缆走向限制",
        "通道间距约 1 m，垂向分辨率受道间距与源检距控制",
        "光纤-地层耦合、温度漂移与相位解缠影响数据质量",
        "设备与施工成本高，需专业解调仪",
    ],
}

TARGET_EXTRA_LIMITATIONS: dict[str, dict[str, str]] = {
    "污染羽": {
        "DC": "只能给出电性异常，不能识别污染物种类与浓度，需钻孔取样与地球化学分析验证",
        "FDEM": "电导率异常受黏土含量与矿化度共同控制，需多频/多装置约束",
    },
    "地下管线": {
        "GPR": "非金属管线反射弱，管径小、充水或埋深大于 3 m 时可能漏检",
        "磁法": "混凝土/PVC 管线无磁响应；金属管线的磁异常与钢筋、围栏等铁质构件难以区分",
    },
    "溶洞": {
        "DC": "空洞（高阻）与黏土充填（低阻）响应相反，存在等值性",
        "GPR": "充水、充泥溶洞衰减明显增大，深部信号弱",
    },
    "含水层": {
        "DC": "低阻异常可能是含水层，也可能是黏土层，需钻孔水位与岩性约束",
    },
    "UXO": {
        "磁法": "探测概率随埋深、目标尺寸和方位变化，不能保证 100% 检出",
        "FDEM": "铁质碎片与土壤电导率变化会产生大量假异常",
    },
    "土层液化": {
        "面波": "Vs 与液化势为经验关系，需 SPT/CPT 标定",
        "DAS": "需钻孔或既有光缆，且只能提供 Vs，不能直接判定液化",
    },
}

PHYSICS_BASIS: dict[str, str] = {
    "GPR": "电磁波在介电界面反射，衰减由电导率与频率决定（趋肤深度 δ≈503√(ρ/f)）",
    "DC": "人工直流电场，视电阻率反映介质导电性差异（ρa=K·ΔV/I）",
    "面波": "瑞利波频散，低频探测深部、高频探测浅部，反演 Vs 分层",
    "磁法": "铁磁体的感应/剩余磁化产生偶极异常，异常随距离三次方衰减",
    "FDEM": "交变一次场在导体中感应涡流，二次场与一次场之比反映电导率",
    "DAS": "光纤瑞利散射的相位变化测量应变率，沿光纤连续观测振动",
}

DEPLOYMENT_REQUIREMENT: dict[str, str] = {
    "GPR": "地表拖曳或手推天线，无需钻孔",
    "DC": "需要电极接地与较长排列，场地开阔度要求高",
    "面波": "需要直线排列与震源（锤击/落重），场地长度约 2–3 倍目标深度",
    "磁法": "手持或拖曳磁力仪，需避开金属设施",
    "FDEM": "手持线圈沿测线行走，需避开电力线与金属栅栏",
    "DAS": "需钻孔内光缆或既有通信光缆；无光缆时无法开展",
}

DISCLAIMER = (
    "本表为《工程地球物理导论》课程知识整理的教学用经验区间，"
    "最大探测深度指最佳配置、低噪声条件下的上限，实际受场地噪声、目标尺寸、含水率影响，"
    "必须通过现场试验剖面标定，不能替代现场工程师判断。"
)


# ============================================================
# 5. 归一化与查表函数
# ============================================================
def normalize_medium(value: str) -> str | None:
    """把用户/模型给的介质描述映射到规范介质名，识别不了返回 None。"""
    if not value:
        return None
    text = str(value).strip().lower()
    for canonical, aliases in MEDIUM_ALIASES.items():
        if any(alias.lower() in text for alias in aliases):
            return canonical
    return None


def normalize_target(value: str) -> str | None:
    """把探测目标描述映射到规范目标名，识别不了返回 None。"""
    if not value:
        return None
    text = str(value).strip().lower()
    for canonical, aliases in TARGET_ALIASES.items():
        if any(alias.lower() in text for alias in aliases):
            return canonical
    return None


def coerce_depth(value: Any) -> float:
    """把埋深转换成 float；允许 "5~12 m" 这类范围，取最大值作为最不利校核深度。"""
    if isinstance(value, bool):
        raise TypeError("target_depth 必须是数字（单位 m），不能是布尔值")
    if isinstance(value, (int, float)):
        depth = float(value)
    else:
        text = str(value)
        numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
        if not numbers:
            raise ValueError(f"无法从 target_depth='{value}' 中解析出埋深数字")
        depth = max(numbers)

    if depth <= 0:
        raise ValueError(f"target_depth 必须大于 0 m，当前为 {depth}")
    if depth > 300:
        raise ValueError(f"target_depth={depth} m 超出本工具适用范围（0–300 m）")
    return round(depth, 2)


def _depth_check(max_depth: float, depth: float) -> tuple[bool, str, float]:
    """返回 (是否满足, 深度校核文字, 深度余量倍数)。"""
    ratio = round(max_depth / depth, 2) if depth else 0.0
    if ratio >= 1.6:
        return True, f"满足（余量 {ratio:.1f}×）", ratio
    if ratio >= 1.0:
        return True, f"临界（余量 {ratio:.1f}×）", ratio
    return False, f"超限（{depth:g} m > {max_depth:g} m）", ratio


def _suitability(
    target: str, method: str, medium: str, max_depth: float, depth: float
) -> tuple[str, str]:
    """按"深度是否覆盖 -> 目标是否有物性响应 -> 介质是否限制"的顺序判定适用性。"""
    feasible, _, _ = _depth_check(max_depth, depth)
    base = BASE_SUITABILITY[target][method]

    if not feasible:
        return "不适用", f"最大探测深度 {max_depth:g} m < 目标埋深 {depth:g} m，无法可靠覆盖目标"

    if base == "不适用":
        specific = INAPPLICABLE_REASON.get((method, target))
        return (
            "不适用",
            specific or f"该方法不测量{target}所依赖的物性（{TARGET_CONTRAST[target]}），不宜采用",
        )

    constraint = MEDIUM_CONSTRAINTS.get(method, {}).get(medium)
    if constraint and base in ("首选", "适用"):
        return "受限", f"{constraint}，因此判为受限（需调整配置或改换方法）"

    reason_map = {
        "首选": "物性差异直接、深度与分辨率满足目标要求，适合作为主方法",
        "适用": "对本目标有效，深度满足，可作为辅助或交叉验证方法",
        "辅助": "可提供间接约束，通常作为辅助手段，不单独定案",
    }
    return base, reason_map.get(base, "可作为参考方法")


def _limitations(target: str, method: str, medium: str, limit: int = 5) -> list[str]:
    """组合基础限制、介质限制与目标限制，去重后截断到 limit 条。"""
    items: list[str] = list(BASE_LIMITATIONS[method])

    constraint = MEDIUM_CONSTRAINTS.get(method, {}).get(medium)
    if constraint:
        # GPR/FDEM 的第 1 条基础限制与本介质的衰减限制重复，去掉后换成具体介质的说法
        if method in ("GPR", "FDEM"):
            items = items[1:]
        items.insert(0, constraint)

    extra = TARGET_EXTRA_LIMITATIONS.get(target, {}).get(method)
    if extra:
        items.insert(0, extra)

    # 去重但保持顺序
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:limit]


def build_method_entry(method: str, target: str, medium: str, depth: float) -> dict[str, Any]:
    """构造单个方法的查表结果。"""
    if method == "DAS":
        max_depth = 50.0
    else:
        max_depth = round(BASE_MAX_DEPTH[method][medium] * TARGET_DEPTH_FACTOR[method][target], 1)

    feasible, check_text, ratio = _depth_check(max_depth, depth)
    suitability, reason = _suitability(target, method, medium, max_depth, depth)

    return {
        "method_cn": METHOD_CN[method],
        "max_depth_m": max_depth,
        "vertical_resolution": RESOLUTION[method],
        "relative_cost": RELATIVE_COST[method],
        "key_limitations": _limitations(target, method, medium),
        "physics_basis": PHYSICS_BASIS[method],
        "deployment_requirement": DEPLOYMENT_REQUIREMENT[method],
        "depth_feasible": feasible,
        "depth_check": check_text,
        "depth_margin_ratio": round(ratio, 2),
        "suitability": suitability,
        "suitability_reason": reason,
    }


def build_lookup_result(
    target: str, medium: str, depth: float, raw_input: dict[str, Any]
) -> dict[str, Any]:
    """构造工具的完整 JSON 返回（六种方法 + 汇总 + 提示）。"""
    methods = {method: build_method_entry(method, target, medium, depth) for method in METHOD_ORDER}

    feasible_methods = [
        m
        for m in METHOD_ORDER
        if methods[m]["depth_feasible"] and methods[m]["suitability"] != "不适用"
    ]
    infeasible_methods = [m for m in METHOD_ORDER if not methods[m]["depth_feasible"]]
    primary = [m for m in METHOD_ORDER if methods[m]["suitability"] == "首选"]
    support = [m for m in METHOD_ORDER if methods[m]["suitability"] in ("适用", "辅助", "受限")]

    warnings: list[str] = []
    for method in infeasible_methods:
        warnings.append(
            f"{METHOD_CN[method]} 最大探测深度 {methods[method]['max_depth_m']:g} m "
            f"< 目标埋深 {depth:g} m，无法覆盖目标"
        )
    if "DAS" in feasible_methods:
        warnings.append("DAS 需要钻孔内光缆或既有通信光缆，若场地不具备则不能作为独立方法")
    if target in ("污染羽", "含水层") and "磁法" in methods:
        warnings.append("磁法对污染羽/含水层没有直接物性响应，只能用于排查铁磁干扰或管线")
    if medium == "填土":
        warnings.append("填土中常含建筑垃圾、钢筋，GPR 与 DC 都可能出现强干扰，需先做试验剖面")
    if not primary:
        warnings.append("当前条件下没有“首选”方法，建议先做方法试验或分深度段设计")

    return {
        "ok": True,
        "tool": "geophysical_param_lookup",
        "query": {
            "target_name": raw_input.get("target_name"),
            "medium": raw_input.get("medium"),
            "target_depth": raw_input.get("target_depth"),
        },
        "normalized": {
            "target": target,
            "medium": medium,
            "depth_m": depth,
            # 输入是 "5~12" 这类范围时说明取的是上限
            "depth_basis": (
                "目标埋深取范围上限，作为最不利校核深度"
                if len(re.findall(r"\d+(?:\.\d+)?", str(raw_input.get("target_depth", "")))) > 1
                else "按输入埋深校核"
            ),
        },
        "target_contrast": TARGET_CONTRAST[target],
        "target_note": TARGET_NOTES[target],
        "methods": methods,
        "summary": {
            "feasible_methods": feasible_methods,
            "infeasible_methods": infeasible_methods,
            "primary_candidates": primary,
            "support_candidates": support,
        },
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }
