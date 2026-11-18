"""八种方法的元数据：物理依据、部署要求、成本量级、通用局限。

这里的成本指数是**教学用相对值**（以每 100 m 测线为基准，GPR=1.0），
只用于方案之间的相对比较，不代表任何市场报价。
"""

from __future__ import annotations

from dataclasses import dataclass

from geophysics_agent.domain.enums import Interference, Method


@dataclass(frozen=True)
class MethodMeta:
    """一种方法的静态属性。"""

    physics_basis: str
    deployment_requirement: str
    relative_cost: str
    cost_index_per_100m: float
    base_limitations: tuple[str, ...]


METHOD_META: dict[Method, MethodMeta] = {
    Method.GPR: MethodMeta(
        physics_basis="电磁波在介电界面反射，衰减由电导率与频率共同决定（趋肤深度 δ≈503√(ρ/f)）",
        deployment_requirement="地表拖曳或手推天线，无需钻孔；要求天线与地表耦合良好",
        relative_cost="低",
        cost_index_per_100m=1.0,
        base_limitations=(
            "高电导介质（湿黏土、含水层、盐渍土）中电磁波强衰减，有效深度骤减",
            "钢筋网、围栏、金属管线产生强反射并屏蔽下方目标",
            "介电常数未知时深度换算误差可达 10%–20%",
            "天线频率越高分辨率越高、穿透越浅，需按目标深度权衡",
            "点距过大会漏掉小口径目标，过小则外业效率低",
        ),
    ),
    Method.DC: MethodMeta(
        physics_basis="人工直流电场，视电阻率反映介质导电性差异（ρa=K·ΔV/I）",
        deployment_requirement="需要电极接地与较长排列，场地开阔度与接地条件要求高",
        relative_cost="中",
        cost_index_per_100m=3.0,
        base_limitations=(
            "反演非唯一性（等值性），薄层与低阻围岩中的目标难以分辨",
            "金属管线、围栏、电力接地使电流畸变，产生假异常",
            "高阻基岩、混凝土地面接地困难，需浇水、换电极位置或加长电极",
            "探测深度受排列长度限制，深部横向分辨率下降",
            "数据量大，反演与解释周期较长",
        ),
    ),
    Method.SURFACE_WAVE: MethodMeta(
        physics_basis="瑞利波频散：低频携带深部信息、高频携带浅部信息，反演得到分层 Vs",
        deployment_requirement="需要直线排列与震源（锤击/落重），排列长度约为目标深度的 2–3 倍",
        relative_cost="低",
        cost_index_per_100m=2.0,
        base_limitations=(
            "1D 水平层状假设，横向分辨率低，复杂地形与陡界面不可靠",
            "城市交通与机械振动降低信噪比",
            "软土低速层导致速度反转，需多模式反演",
            "目标尺寸小于波长时响应弱，难以识别小尺度异常体",
            "只能给出 Vs 结构，不能直接识别目标属性",
        ),
    ),
    Method.MAGNETIC: MethodMeta(
        physics_basis="铁磁体的感应/剩余磁化产生偶极异常，异常幅度随距离三次方衰减",
        deployment_requirement="手持或拖曳磁力仪沿测线行走，需避开金属设施与车辆",
        relative_cost="低",
        cost_index_per_100m=1.0,
        base_limitations=(
            "仅对铁磁性（铁、钢）目标有效，对非铁磁目标没有直接响应",
            "钢筋、围栏、车辆、电力线的人文干扰强",
            "无垂向分辨能力，深度需多高度测量或梯度反演",
            "异常幅度随距离三次方衰减，小目标随埋深迅速失效",
            "日变与仪器漂移需要静态改正",
        ),
    ),
    Method.FDEM: MethodMeta(
        physics_basis="交变一次场在导体中感应涡流，二次场与一次场之比反映视电导率",
        deployment_requirement="手持线圈沿测线行走，需避开电力线与金属栅栏",
        relative_cost="中",
        cost_index_per_100m=2.0,
        base_limitations=(
            "高导覆盖层（黏土、盐渍土、含水层）屏蔽深部响应",
            "金属管线、围栏强响应压制小目标",
            "扩散场垂向分辨率低，层状解释多解",
            "响应受线圈姿态与背景电导率影响，需相对测量与零点校正",
            "探测深度与线圈距、频率强相关，需按目标深度选配置",
        ),
    ),
    Method.REFRACTION: MethodMeta(
        physics_basis="折射波沿速度界面传播，首波到达时间反映界面深度与层速度（临界折射/首波）",
        deployment_requirement="需要直线排列与可控震源（锤击/落重），排列长度约为目标深度的 3–5 倍",
        relative_cost="低",
        cost_index_per_100m=2.5,
        base_limitations=(
            "低速层可造成速度反转/隐藏层问题，折射解释需谨慎",
            "只对速度随深度增大的层状介质有效，横向分辨率低",
            "城市交通与机械振动降低首波信噪比",
            "目标尺寸远小于排列长度时响应弱，无法识别小尺度异常体",
            "只能给出速度分层，不能直接识别岩性/承载力",
        ),
    ),
    Method.TEM: MethodMeta(
        physics_basis="发射电流关断后，地下导体感应的二次场随时间扩散衰减（烟圈扩散），晚时间对应深部",
        deployment_requirement="铺设发射回线，接收线圈测量二次场衰减；需避开强电磁干扰",
        relative_cost="中",
        cost_index_per_100m=4.0,
        base_limitations=(
            "扩散场垂向分辨率低，层状解释多解",
            "电力线、管线等强电磁干扰压制信号",
            "浅部存在早期时间盲区，受发射关断影响",
            "高导覆盖层会屏蔽深部响应",
            "针对具体目标需数值模拟评估可探测性",
        ),
    ),
    Method.DAS: MethodMeta(
        physics_basis="光纤瑞利散射的相位变化测量应变率，沿光纤连续观测振动",
        deployment_requirement="需要钻孔内光缆或既有通信光缆；无光缆时无法开展",
        relative_cost="高",
        cost_index_per_100m=15.0,
        base_limitations=(
            "需要钻孔内光缆或既有通信光缆，场地条件限制大",
            "仅测量沿光纤一维应变/振动，空间覆盖受光缆走向限制",
            "通道间距约 1 m，垂向分辨率受道间距与源检距控制",
            "光纤-地层耦合、温度漂移与相位解缠影响数据质量",
            "设备与施工成本高，需专业解调仪与数据处理能力",
        ),
    ),
}


# 干扰对方法的压制关系：命中即把"首选/适用"降为"受限"，并给出具体理由。
INTERFERENCE_CONSTRAINTS: dict[Method, dict[Interference, str]] = {
    Method.GPR: {
        Interference.REBAR: "钢筋混凝土地面与钢筋网产生强反射，屏蔽下方目标并形成多次波",
        Interference.FENCE: "金属围栏/铁栅形成强点状反射，干扰识别",
        Interference.MACHINERY: "施工机械的金属体与振动破坏天线耦合与剖面连续性",
        Interference.TERRAIN: "地形起伏与碎石覆盖造成天线耦合不稳、静校正困难",
    },
    Method.DC: {
        Interference.REBAR: "钢筋与金属管线使地下电流畸变，产生低阻假异常",
        Interference.POWERLINE: "电力线接地电流与 50 Hz 干扰降低信噪比",
        Interference.TERRAIN: "地形起伏使电极高程与排列几何失真，必须做地形改正",
    },
    Method.SURFACE_WAVE: {
        Interference.VIBRATION: "持续振动抬高背景噪声，频散曲线提取不稳定",
        Interference.TRAFFIC: "交通振动与车辆通过造成瞬态强噪声",
        Interference.MACHINERY: "施工机械振动与撞击破坏面波记录质量",
    },
    Method.MAGNETIC: {
        Interference.REBAR: "钢筋、铁质构件产生强磁异常，掩盖目标信号",
        Interference.FENCE: "铁栅与围栏形成线状强磁异常",
        Interference.MACHINERY: "施工机械与车辆的铁磁体造成大幅干扰",
        Interference.POWERLINE: "电力线的电磁干扰与接地电流影响磁力仪读数",
    },
    Method.FDEM: {
        Interference.POWERLINE: "电力线产生强电磁干扰，需远离或改频观测",
        Interference.FENCE: "金属栅栏形成强响应，压制小目标异常",
        Interference.MACHINERY: "施工机械金属体产生强响应，干扰剖面解释",
    },
    Method.REFRACTION: {
        Interference.VIBRATION: "持续振动抬高背景噪声，首波拾取不稳定",
        Interference.TRAFFIC: "交通振动与车辆通过造成瞬态强噪声",
        Interference.MACHINERY: "施工机械振动与撞击破坏首波记录质量",
    },
    Method.TEM: {
        Interference.POWERLINE: "电力线强电磁干扰严重压制二次场信号",
        Interference.FENCE: "金属栅栏产生强响应，干扰剖面解释",
        Interference.MACHINERY: "施工机械金属体产生强响应",
        Interference.REBAR: "钢筋网产生浅层强响应，压制目标信号",
    },
    Method.DAS: {},
}


#: "严重干扰"：会实质毁掉该方法的数据质量，命中后适用性直接降为"受限"。
#: 其余干扰只作为方案限制说明，通过施工措施（避让、改频、地形改正）缓解。
SEVERE_INTERFERENCE: dict[Method, frozenset[Interference]] = {
    Method.GPR: frozenset(),
    Method.DC: frozenset({Interference.REBAR, Interference.POWERLINE}),
    Method.SURFACE_WAVE: frozenset(),
    Method.REFRACTION: frozenset(),
    Method.MAGNETIC: frozenset(
        {Interference.REBAR, Interference.FENCE, Interference.MACHINERY, Interference.POWERLINE}
    ),
    Method.FDEM: frozenset({Interference.FENCE, Interference.MACHINERY, Interference.POWERLINE}),
    Method.TEM: frozenset({Interference.POWERLINE, Interference.FENCE, Interference.MACHINERY}),
    Method.DAS: frozenset(),
}
