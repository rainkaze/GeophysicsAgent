import json
import math
import re
METHOD_ORDER = ('gpr', 'dc', 'surface_wave', 'refraction', 'magnetic', 'fdem', 'tem', 'das')
METHOD_CN = {'gpr': '探地雷达（GPR）', 'dc': '直流电阻率（DC/ERT）', 'surface_wave': '面波地震（MASW）', 'refraction': '地震折射（Refraction）', 'magnetic': '磁法勘探', 'fdem': '频域电磁（FDEM）', 'tem': '瞬变电磁（TEM）', 'das': '分布式光纤声学（DAS）'}
TARGET_CN = {'plume': '污染羽', 'utility': '地下管线', 'karst': '溶洞与空洞', 'aquifer': '含水层', 'uxo': 'UXO 未爆物', 'liquefaction': '土层液化', 'site_investigation': '工程勘察'}
MEDIUM_CN = {'clay': '黏土', 'silt': '粉土', 'sand': '砂土', 'fill': '填土', 'limestone': '灰岩', 'bedrock': '基岩', 'soft_soil': '软土'}
INTERFERENCE_CN = {'rebar': '钢筋与金属构筑物', 'powerline': '电力线/高压线', 'traffic': '交通车辆', 'machinery': '施工机械', 'fence': '围栏铁栅', 'vibration': '持续振动', 'terrain': '地形起伏'}
SURFACE_CN = {'paved': '硬化路面', 'grass': '农田草地', 'gravel': '碎石覆盖', 'water': '水域', 'unknown': '未说明'}
BUDGET_CN = {'low': '偏低', 'medium': '中等', 'high': '充足'}
TARGET_PRIORITY = ('utility', 'plume', 'karst', 'uxo', 'liquefaction', 'aquifer', 'site_investigation')
TARGET_ALIASES = {'utility': ('管线', '管道', 'pipe', '电缆', '混凝土管', '地下管'), 'plume': ('污染', '羽', 'plume', 'contaminant', '污染物'), 'karst': ('溶洞', '空洞', '岩溶', 'karst', 'cavity', 'void', '土洞', '脱空'), 'uxo': ('uxo', '未爆', '炸弹', '弹药', '爆炸物'), 'liquefaction': ('液化', 'liquefaction'), 'aquifer': ('含水层', '地下水', 'aquifer'), 'site_investigation': ('勘察', 'site investigation', 'geotechnical', '地层分层', '覆盖层', '基岩面', '地基')}
MEDIUM_PRIORITY = ('limestone', 'bedrock', 'soft_soil', 'clay', 'silt', 'sand', 'fill')
MEDIUM_ALIASES = {'limestone': ('灰岩', '石灰岩', 'limestone', '碳酸盐岩'), 'bedrock': ('基岩', 'bedrock', '岩石', '强风化'), 'soft_soil': ('软土', '淤泥', 'soft soil', 'mud', '软黏土'), 'clay': ('黏土', '粘土', 'clay', '粉质黏土'), 'silt': ('粉土', 'silt', '粉砂'), 'sand': ('砂土', '砂层', 'sand', '砂砾', '砾砂'), 'fill': ('填土', '回填', '杂填', '素填', 'fill')}
TARGET_CONTRAST = {'plume': '电阻率/电导率差异（TDS、离子浓度、NAPL 影响）', 'utility': '金属的高电导率/高磁化率，或管壁与土的介电、波阻抗差异', 'karst': '空洞与围岩的电阻率、介电常数、波速差异', 'aquifer': '含水层与隔水层的电阻率差异、Vs 差异', 'uxo': '铁磁体的磁化率异常与金属高电导率', 'liquefaction': '液化砂层与上覆层的 Vs、密度差异', 'site_investigation': '地层波速、电阻率、介电差异'}
TARGET_NOTES = {'plume': '电阻率异常由 TDS、NAPL 与黏土含量共同控制，异常≠污染物浓度，需钻孔取样验证。', 'utility': '金属管线可用磁法/电磁感应，非金属管线主要靠 GPR 的介电差异。', 'karst': '溶洞可为空洞（高阻）或黏土充填（低阻），电性响应相反，需地质资料约束。', 'aquifer': '低阻异常可能是含水层，也可能是黏土层，需结合岩性与钻孔水位。', 'uxo': '异常幅度随距离三次方衰减，探测概率随埋深/目标尺寸下降，必须按安全规程开挖验证。', 'liquefaction': '液化判别需要 Vs 或 SPT/CPT，加上地下水位与砂层分布，物探只提供速度结构。', 'site_investigation': '物探提供间接参数，需钻孔与原位测试标定后才能用于设计。'}
GPR_TARGET_RESOLUTION_M = {'utility': 0.15, 'uxo': 0.05}
BASE_MAX_DEPTH = {'gpr': {'clay': 3.0, 'soft_soil': 2.0, 'silt': 6.0, 'sand': 15.0, 'fill': 8.0, 'limestone': 20.0, 'bedrock': 15.0}, 'dc': {'clay': 25.0, 'soft_soil': 20.0, 'silt': 30.0, 'sand': 35.0, 'fill': 25.0, 'limestone': 40.0, 'bedrock': 40.0}, 'surface_wave': {'clay': 25.0, 'soft_soil': 30.0, 'silt': 30.0, 'sand': 35.0, 'fill': 20.0, 'limestone': 40.0, 'bedrock': 50.0}, 'magnetic': {'clay': 5.0, 'soft_soil': 5.0, 'silt': 5.0, 'sand': 5.0, 'fill': 5.0, 'limestone': 5.0, 'bedrock': 4.0}, 'fdem': {'clay': 12.0, 'soft_soil': 8.0, 'silt': 15.0, 'sand': 20.0, 'fill': 10.0, 'limestone': 25.0, 'bedrock': 20.0}, 'refraction': {'clay': 25.0, 'soft_soil': 30.0, 'silt': 30.0, 'sand': 35.0, 'fill': 20.0, 'limestone': 40.0, 'bedrock': 50.0}, 'tem': {'clay': 30.0, 'soft_soil': 40.0, 'silt': 50.0, 'sand': 60.0, 'fill': 30.0, 'limestone': 60.0, 'bedrock': 60.0}, 'das': {'clay': 50.0, 'soft_soil': 50.0, 'silt': 50.0, 'sand': 50.0, 'fill': 50.0, 'limestone': 50.0, 'bedrock': 50.0}}
TARGET_DEPTH_FACTOR = {'gpr': {'plume': 0.8, 'utility': 0.6, 'karst': 0.8, 'aquifer': 0.6, 'uxo': 0.8, 'liquefaction': 0.5, 'site_investigation': 1.0}, 'dc': {'plume': 1.0, 'utility': 0.8, 'karst': 1.0, 'aquifer': 1.0, 'uxo': 0.5, 'liquefaction': 1.0, 'site_investigation': 1.0}, 'surface_wave': {'plume': 0.9, 'utility': 0.3, 'karst': 1.0, 'aquifer': 1.0, 'uxo': 0.3, 'liquefaction': 1.0, 'site_investigation': 1.0}, 'magnetic': {'plume': 0.5, 'utility': 1.0, 'karst': 0.6, 'aquifer': 0.5, 'uxo': 0.6, 'liquefaction': 0.5, 'site_investigation': 1.0}, 'fdem': {'plume': 1.0, 'utility': 0.8, 'karst': 1.2, 'aquifer': 1.2, 'uxo': 0.6, 'liquefaction': 1.0, 'site_investigation': 1.0}, 'refraction': {'plume': 0.5, 'utility': 0.3, 'karst': 0.8, 'aquifer': 1.0, 'uxo': 0.3, 'liquefaction': 1.0, 'site_investigation': 1.0}, 'tem': {'plume': 1.0, 'utility': 0.8, 'karst': 1.2, 'aquifer': 1.2, 'uxo': 0.6, 'liquefaction': 1.0, 'site_investigation': 1.0}, 'das': {'plume': 1.0, 'utility': 1.0, 'karst': 1.0, 'aquifer': 1.0, 'uxo': 1.0, 'liquefaction': 1.0, 'site_investigation': 1.0}}
P, A, S, C, N = ('首选', '适用', '辅助', '受限', '不适用')
BASE_SUITABILITY = {'plume': {'gpr': S, 'dc': P, 'surface_wave': S, 'refraction': S, 'magnetic': N, 'fdem': A, 'tem': A, 'das': S}, 'utility': {'gpr': P, 'dc': S, 'surface_wave': N, 'refraction': N, 'magnetic': A, 'fdem': A, 'tem': S, 'das': N}, 'karst': {'gpr': P, 'dc': A, 'surface_wave': A, 'refraction': A, 'magnetic': N, 'fdem': S, 'tem': S, 'das': N}, 'aquifer': {'gpr': S, 'dc': P, 'surface_wave': A, 'refraction': A, 'magnetic': N, 'fdem': A, 'tem': A, 'das': S}, 'uxo': {'gpr': S, 'dc': N, 'surface_wave': N, 'refraction': N, 'magnetic': P, 'fdem': P, 'tem': S, 'das': N}, 'liquefaction': {'gpr': S, 'dc': S, 'surface_wave': P, 'refraction': A, 'magnetic': N, 'fdem': S, 'tem': S, 'das': A}, 'site_investigation': {'gpr': A, 'dc': A, 'surface_wave': P, 'refraction': P, 'magnetic': S, 'fdem': S, 'tem': S, 'das': S}}
MEDIUM_CONSTRAINTS = {'gpr': {'clay': '湿黏土电导率可达约 100 mS/m，电磁波强衰减，有效深度通常仅 1–3 m', 'soft_soil': '软土饱水、电导率高，GPR 衰减大，有效深度通常不足 2 m'}, 'fdem': {'clay': '低阻黏土覆盖层屏蔽深部二次场，需增大线圈距或降低频率', 'soft_soil': '软土高导覆盖层屏蔽深部响应，深部异常弱'}, 'magnetic': {'bedrock': '基岩若含磁铁矿会抬升背景、产生干扰异常'}}
INAPPLICABLE_REASON = {('magnetic', 'plume'): '磁法只对铁磁性（铁、钢）目标有效，污染羽不产生磁异常', ('magnetic', 'aquifer'): '磁法只对铁磁性目标有效，含水层不产生磁异常', ('magnetic', 'liquefaction'): '磁法只对铁磁性目标有效，液化砂层不产生磁异常', ('magnetic', 'karst'): '磁法只对铁磁性目标有效，溶洞不产生磁异常', ('dc', 'uxo'): '直流电阻率对小型金属目标响应弱、分辨率不足，不适合 UXO 探测', ('surface_wave', 'uxo'): '面波分辨率低（米级），无法识别小型 UXO', ('surface_wave', 'utility'): '面波横向分辨率低，难以识别小口径管线', ('das', 'utility'): 'DAS 只测量沿光纤的应变/振动，不能直接探测管线，且需钻孔或既有光缆', ('das', 'karst'): 'DAS 只测量沿光纤的应变/振动，不能直接探测溶洞', ('das', 'uxo'): 'DAS 只测量沿光纤的应变/振动，不能直接探测 UXO', ('refraction', 'utility'): '地震折射垂向分辨率低（米级），无法识别小口径管线', ('refraction', 'uxo'): '地震折射无法识别小型 UXO'}
TARGET_EXTRA_LIMITATIONS = {'plume': {'dc': '只能给出电性异常，不能识别污染物种类与浓度，需钻孔取样与地球化学分析验证', 'fdem': '电导率异常受黏土含量与矿化度共同控制，需多频/多装置约束'}, 'utility': {'gpr': '非金属管线反射弱，管径小、充水或埋深大于 3 m 时可能漏检', 'magnetic': '混凝土/PVC 管线无磁响应；金属管线的磁异常与钢筋、围栏难以区分'}, 'karst': {'dc': '空洞（高阻）与黏土充填（低阻）响应相反，存在等值性', 'gpr': '充水、充泥溶洞衰减明显增大，深部信号弱'}, 'aquifer': {'dc': '低阻异常可能是含水层，也可能是黏土层，需钻孔水位与岩性约束'}, 'uxo': {'magnetic': '探测概率随埋深、目标尺寸和方位变化，不能保证 100% 检出', 'fdem': '铁质碎片与土壤电导率变化会产生大量假异常'}, 'liquefaction': {'surface_wave': 'Vs 与液化势为经验关系，需 SPT/CPT 标定', 'das': '需钻孔或既有光缆，且只能提供 Vs，不能直接判定液化'}}
DISCLAIMER = '本结果为课程演示级辅助建议。最大探测深度为教学用经验上限，实际受场地噪声、目标尺寸与含水状态影响，必须经现场试验剖面标定；物探解释具有多解性，需结合钻孔、原位测试及工程师判断。'
METHOD_META = {'gpr': {'physics_basis': '电磁波在介电界面反射，衰减由电导率与频率共同决定（趋肤深度 δ≈503√(ρ/f)）', 'deployment_requirement': '地表拖曳或手推天线，无需钻孔；要求天线与地表耦合良好', 'relative_cost': '低', 'cost_index': 1.0, 'base_limitations': ('高电导介质（湿黏土、含水层、盐渍土）中电磁波强衰减，有效深度骤减', '钢筋网、围栏、金属管线产生强反射并屏蔽下方目标', '介电常数未知时深度换算误差可达 10%–20%', '天线频率越高分辨率越高、穿透越浅，需按目标深度权衡', '点距过大会漏掉小口径目标，过小则外业效率低')}, 'dc': {'physics_basis': '人工直流电场，视电阻率反映介质导电性差异（ρa=K·ΔV/I）', 'deployment_requirement': '需要电极接地与较长排列，场地开阔度与接地条件要求高', 'relative_cost': '中', 'cost_index': 3.0, 'base_limitations': ('反演非唯一性（等值性），薄层与低阻围岩中的目标难以分辨', '金属管线、围栏、电力接地使电流畸变，产生假异常', '高阻基岩、混凝土地面接地困难，需浇水、换电极位置或加长电极', '探测深度受排列长度限制，深部横向分辨率下降', '数据量大，反演与解释周期较长')}, 'surface_wave': {'physics_basis': '瑞利波频散：低频携带深部信息、高频携带浅部信息，反演得到分层 Vs', 'deployment_requirement': '需要直线排列与震源（锤击/落重），排列长度约为目标深度的 2–3 倍', 'relative_cost': '低', 'cost_index': 2.0, 'base_limitations': ('1D 水平层状假设，横向分辨率低，复杂地形与陡界面不可靠', '城市交通与机械振动降低信噪比', '软土低速层导致速度反转，需多模式反演', '目标尺寸小于波长时响应弱，难以识别小尺度异常体', '只能给出 Vs 结构，不能直接识别目标属性')}, 'refraction': {'physics_basis': '折射波沿速度界面传播，首波到达时间反映界面深度与层速度（临界折射/首波）', 'deployment_requirement': '需要直线排列与可控震源（锤击/落重），排列长度约为目标深度的 3–5 倍', 'relative_cost': '低', 'cost_index': 2.5, 'base_limitations': ('低速层可造成速度反转/隐藏层问题，折射解释需谨慎', '只对速度随深度增大的层状介质有效，横向分辨率低', '城市交通与机械振动降低首波信噪比', '目标尺寸远小于排列长度时响应弱，无法识别小尺度异常体', '只能给出速度分层，不能直接识别岩性/承载力')}, 'magnetic': {'physics_basis': '铁磁体的感应/剩余磁化产生偶极异常，异常幅度随距离三次方衰减', 'deployment_requirement': '手持或拖曳磁力仪沿测线行走，需避开金属设施与车辆', 'relative_cost': '低', 'cost_index': 1.0, 'base_limitations': ('仅对铁磁性（铁、钢）目标有效，对非铁磁目标没有直接响应', '钢筋、围栏、车辆、电力线的人文干扰强', '无垂向分辨能力，深度需多高度测量或梯度反演', '异常幅度随距离三次方衰减，小目标随埋深迅速失效', '日变与仪器漂移需要静态改正')}, 'fdem': {'physics_basis': '交变一次场在导体中感应涡流，二次场与一次场之比反映视电导率', 'deployment_requirement': '手持线圈沿测线行走，需避开电力线与金属栅栏', 'relative_cost': '中', 'cost_index': 2.0, 'base_limitations': ('高导覆盖层（黏土、盐渍土、含水层）屏蔽深部响应', '金属管线、围栏强响应压制小目标', '扩散场垂向分辨率低，层状解释多解', '响应受线圈姿态与背景电导率影响，需相对测量与零点校正', '探测深度与线圈距、频率强相关，需按目标深度选配置')}, 'tem': {'physics_basis': '发射电流关断后，地下导体感应的二次场随时间扩散衰减（烟圈扩散），晚时间对应深部', 'deployment_requirement': '铺设发射回线，接收线圈测量二次场衰减；需避开强电磁干扰', 'relative_cost': '中', 'cost_index': 4.0, 'base_limitations': ('扩散场垂向分辨率低，层状解释多解', '电力线、管线等强电磁干扰压制信号', '浅部存在早期时间盲区，受发射关断影响', '高导覆盖层会屏蔽深部响应', '针对具体目标需数值模拟评估可探测性')}, 'das': {'physics_basis': '光纤瑞利散射的相位变化测量应变率，沿光纤连续观测振动', 'deployment_requirement': '需要钻孔内光缆或既有通信光缆；无光缆时无法开展', 'relative_cost': '高', 'cost_index': 15.0, 'base_limitations': ('需要钻孔内光缆或既有通信光缆，场地条件限制大', '仅测量沿光纤一维应变/振动，空间覆盖受光缆走向限制', '通道间距约 1 m，垂向分辨率受道间距与源检距控制', '光纤-地层耦合、温度漂移与相位解缠影响数据质量', '设备与施工成本高，需专业解调仪与数据处理能力')}}
INTERFERENCE_CONSTRAINTS = {'gpr': {'rebar': '钢筋混凝土地面与钢筋网产生强反射，屏蔽下方目标并形成多次波', 'fence': '金属围栏/铁栅形成强点状反射，干扰识别', 'machinery': '施工机械的金属体与振动破坏天线耦合与剖面连续性', 'terrain': '地形起伏与碎石覆盖造成天线耦合不稳、静校正困难'}, 'dc': {'rebar': '钢筋与金属管线使地下电流畸变，产生低阻假异常', 'powerline': '电力线接地电流与 50 Hz 干扰降低信噪比', 'terrain': '地形起伏使电极高程与排列几何失真，必须做地形改正'}, 'surface_wave': {'vibration': '持续振动抬高背景噪声，频散曲线提取不稳定', 'traffic': '交通振动与车辆通过造成瞬态强噪声', 'machinery': '施工机械振动与撞击破坏面波记录质量'}, 'magnetic': {'rebar': '钢筋、铁质构件产生强磁异常，掩盖目标信号', 'fence': '铁栅与围栏形成线状强磁异常', 'machinery': '施工机械与车辆的铁磁体造成大幅干扰', 'powerline': '电力线的电磁干扰与接地电流影响磁力仪读数'}, 'fdem': {'powerline': '电力线产生强电磁干扰，需远离或改频观测', 'fence': '金属栅栏形成强响应，压制小目标异常', 'machinery': '施工机械金属体产生强响应，干扰剖面解释'}, 'refraction': {'vibration': '持续振动抬高背景噪声，首波拾取不稳定', 'traffic': '交通振动与车辆通过造成瞬态强噪声', 'machinery': '施工机械振动与撞击破坏首波记录质量'}, 'tem': {'powerline': '电力线强电磁干扰严重压制二次场信号', 'fence': '金属栅栏产生强响应，干扰剖面解释', 'machinery': '施工机械金属体产生强响应', 'rebar': '钢筋网产生浅层强响应，压制目标信号'}, 'das': {}}
SEVERE_INTERFERENCE = {'gpr': frozenset(), 'dc': frozenset({'rebar', 'powerline'}), 'surface_wave': frozenset(), 'refraction': frozenset(), 'magnetic': frozenset({'rebar', 'fence', 'machinery', 'powerline'}), 'fdem': frozenset({'fence', 'machinery', 'powerline'}), 'tem': frozenset({'powerline', 'fence', 'machinery'}), 'das': frozenset()}
LIGHT_SPEED_M_PER_NS = 0.3
RELATIVE_PERMITTIVITY = {'clay': 12.0, 'silt': 8.0, 'sand': 6.0, 'fill': 8.0, 'limestone': 7.0, 'bedrock': 7.0, 'soft_soil': 15.0}
GPR_ANTENNAS_MHZ = (1000.0, 500.0, 250.0, 100.0, 50.0)
GPR_BASE_FREQ_MHZ = 100.0
DC_DEPTH_TO_ARRAY = 0.25
SURFACE_WAVE_ARRAY_TO_DEPTH = 2.5
MARGIN_SATISFY = 1.6
MARGIN_CRITICAL = 1.15
MARGIN_FEASIBLE = 1.0
_BASE_REASON = {P: '物性差异直接、深度与分辨率满足目标要求，适合作为主方法', A: '对本目标有效且深度满足，可作为辅助或交叉验证方法', S: '可提供间接约束，通常作为辅助手段，不单独定案', C: '存在明确限制，需调整配置或改换方法'}

def _gpr_velocity(medium: str) -> float:
    return LIGHT_SPEED_M_PER_NS / math.sqrt(RELATIVE_PERMITTIVITY[medium])

def _gpr_wavelength(medium: str, frequency_mhz: float) -> float:
    return _gpr_velocity(medium) * 1000.0 / frequency_mhz

def _gpr_reachable(base_depth_m: float, frequency_mhz: float) -> float:
    return base_depth_m * math.sqrt(GPR_BASE_FREQ_MHZ / frequency_mhz)

def design_gpr(medium, required_depth_m, base_depth_m, min_resolution_m=None):
    safety = 1.3
    velocity = _gpr_velocity(medium)

    def resolution_of(frequency_mhz):
        return _gpr_wavelength(medium, frequency_mhz) / 4.0
    chosen = GPR_ANTENNAS_MHZ[-1]
    for frequency in GPR_ANTENNAS_MHZ:
        reachable = _gpr_reachable(base_depth_m, frequency)
        ok_resolution = min_resolution_m is None or resolution_of(frequency) <= min_resolution_m
        if reachable >= required_depth_m * safety and ok_resolution:
            chosen = frequency
            break
    resolution_limited = False
    if min_resolution_m is not None and resolution_of(chosen) > min_resolution_m:
        for frequency in reversed(GPR_ANTENNAS_MHZ):
            if resolution_of(frequency) <= min_resolution_m:
                chosen = frequency
                resolution_limited = True
                break
    reachable = _gpr_reachable(base_depth_m, chosen)
    wavelength = _gpr_wavelength(medium, chosen)
    resolution = wavelength / 4.0
    window = 2.0 * required_depth_m * safety / velocity
    spacing = min(0.5, max(0.05, round(resolution / 4.0, 2)))
    note = f'按 εr={RELATIVE_PERMITTIVITY[medium]:g} 得 v={velocity:.3f} m/ns，选 {chosen:g} MHz（经验可达 {reachable:.1f} m，需覆盖 1.3×目标深度）；λ={wavelength:.2f} m，分辨率按 λ/4 取 {resolution:.2f} m；时窗按 t=2d/v 取 {window:.0f} ns'
    if resolution_limited:
        note += f'；受小目标尺寸限制，{chosen:g} MHz 的深度覆盖可能不足，需低频复核或加密点距'
    return {'antenna_mhz': chosen, 'reachable_depth_m': round(reachable, 1), 'resolution_m': round(resolution, 2), 'window_ns': round(window, 0), 'point_spacing_m': spacing, 'note': note}

def design_dc(depth_m, electrodes=48):
    needed = depth_m / DC_DEPTH_TO_ARRAY
    ladder = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0, 15.0, 20.0)
    spacing = ladder[-1]
    for candidate in ladder:
        if candidate * (electrodes - 1) >= needed:
            spacing = candidate
            break
    array_length = spacing * (electrodes - 1)
    resolution = 0.15 * depth_m
    note = f'有效深度≈0.25×排列长度，目标 {depth_m:g} m 需排列长约 {needed:.0f} m；{electrodes} 道电极取电极距 {spacing:g} m，实际排列长 {array_length:g} m；垂向分辨率按 0.15×深度估约 {resolution:.1f} m'
    return {'array_length_m': round(array_length, 1), 'spacing_m': spacing, 'channels': electrodes, 'resolution_m': round(resolution, 1), 'note': note}

def design_surface_wave(depth_m, channels=24):
    needed = depth_m * SURFACE_WAVE_ARRAY_TO_DEPTH
    spacing = max(1.0, math.ceil(needed / (channels - 1) * 2.0) / 2.0)
    array_length = spacing * (channels - 1)
    resolution = 0.2 * depth_m
    note = f'排列长度取 2.5×目标深度≈{needed:.0f} m；{channels} 道取道间距 {spacing:g} m，实际排列长 {array_length:g} m；分层分辨率按 0.2×深度估约 {resolution:.1f} m'
    return {'array_length_m': round(array_length, 1), 'spacing_m': spacing, 'channels': channels, 'resolution_m': round(resolution, 1), 'note': note}

def design_refraction(depth_m, channels=24):
    needed = depth_m * 4.0
    spacing = max(1.0, math.ceil(needed / (channels - 1) * 2.0) / 2.0)
    array_length = spacing * (channels - 1)
    resolution = 0.2 * depth_m
    note = f'有效深度≈0.25×排列长度，目标 {depth_m:g} m 需排列长约 {needed:.0f} m；{channels} 道取道间距 {spacing:g} m，实际排列长 {array_length:g} m；分层分辨率按 0.2×深度估约 {resolution:.1f} m'
    return {'array_length_m': round(array_length, 1), 'spacing_m': spacing, 'channels': channels, 'resolution_m': round(resolution, 1), 'note': note}

def design_magnetic(depth_m):
    line_spacing = max(1.0, round(depth_m, 1))
    station_spacing = max(0.5, round(depth_m / 2.0, 1))
    return {'line_spacing_m': line_spacing, 'station_spacing_m': station_spacing, 'resolution_m': None, 'note': '磁法无垂向分辨能力，只能平面定位；线距按目标埋深的 1 倍、点距按 0.5 倍布置'}

def design_fdem(depth_m):
    if depth_m <= 6.0:
        coil, band = (3.66, '高频段（约 9.8 kHz）')
    elif depth_m <= 15.0:
        coil, band = (10.0, '中频段（约 1.6–6.4 kHz）')
    else:
        coil, band = (20.0, '低频段（约 0.4–1.6 kHz）')
    station = max(1.0, round(depth_m / 2.0, 1))
    resolution = round(0.4 * depth_m, 1)
    return {'line_spacing_m': coil, 'station_spacing_m': station, 'resolution_m': resolution, 'note': f'按目标 {depth_m:g} m 选线圈距 {coil:g} m、{band}；扩散场垂向分辨率约 0.4×深度≈{resolution:g} m'}

def design_tem(depth_m):
    loop = max(10.0, round(depth_m * 0.5, 0))
    station = max(5.0, round(depth_m * 0.5, 0))
    resolution = round(0.3 * depth_m, 1)
    return {'line_spacing_m': loop, 'station_spacing_m': station, 'resolution_m': resolution, 'note': f'按目标 {depth_m:g} m 建议回线边长约 {loop:g} m、测点距 {station:g} m；扩散场垂向分辨率约 0.3×深度≈{resolution:g} m，深部探测需增大发射磁矩并延长记录时间'}

def design_das(depth_m):
    borehole = depth_m + 10.0
    return {'channel_spacing_m': 1.0, 'borehole_depth_m': round(borehole, 1), 'resolution_m': 1.0, 'note': f'通道间距 1 m；钻孔或既有光缆长度需覆盖目标深度并留 10 m 余量，建议 ≥{borehole:g} m'}
_MAX_PLAUSIBLE_DEPTH_M = 300.0
_RANGE_WITH_CONTEXT = re.compile('(?:埋深|深度|深约|埋藏深度|目标层深度)[^\\d]{0,8}(\\d+(?:\\.\\d+)?)\\s*(?:~|～|-|—|到|至)\\s*(\\d+(?:\\.\\d+)?)')
_SINGLE_WITH_CONTEXT = re.compile('(?:埋深|深度|深约|埋藏深度)[^\\d]{0,8}(\\d+(?:\\.\\d+)?)\\s*(?:m|米)?')
_RANGE_BARE = re.compile('(\\d+(?:\\.\\d+)?)\\s*(?:~|～|-|—|到|至)\\s*(\\d+(?:\\.\\d+)?)\\s*(?:m|米)')
_SINGLE_TRAILING = re.compile('(\\d+(?:\\.\\d+)?)\\s*(?:m|米)\\s*(?:埋深|深度|以深|以内|左右|深)')
_SINGLE_UNIT = re.compile('(\\d+(?:\\.\\d+)?)\\s*(?:m|米)')
_SITE_LENGTH = re.compile('(?:场地|测线|路基)[^，。；]{0,6}?(\\d+(?:\\.\\d+)?)\\s*(?:m|米)')
_INTERFERENCE_RULES = (('rebar', ('钢筋', '钢筋混凝土', '金属设施', '金属构件')), ('powerline', ('电力线', '高压', 'kv', '千伏', '输电线')), ('traffic', ('交通', '车辆', '车流', '行车')), ('machinery', ('施工机械', '机械作业', '施工机具', '钻机')), ('fence', ('围栏', '铁栅', '围挡', '栅栏')), ('terrain', ('地形起伏', '起伏较大', '山地', '陡坡', '地形复杂')), ('vibration', ('振动', '震动', '轻微交通振动', '持续振动')))
_SURFACE_RULES = (('paved', ('沥青', '混凝土', '水泥', '硬化路面', '路面')), ('gravel', ('碎石', '砾石覆盖', '碎石覆盖')), ('water', ('水域', '河道', '湖面', '海上', '水面')), ('grass', ('农田', '草地', '绿化带', '空地', '耕地')))
_NEGATION_WORDS = ('无', '没有', '不存在', '不具备', '未发现', '少见', '少有')

def _is_negated(text, index, window=6):
    prefix = text[max(0, index - window):index]
    return any((word in prefix for word in _NEGATION_WORDS))

def _match_target(text):
    lowered = text.lower()
    for target in TARGET_PRIORITY:
        aliases = sorted(TARGET_ALIASES[target], key=len, reverse=True)
        if any((alias in lowered for alias in aliases)):
            return target
    return None

def _match_medium(text):
    lowered = text.lower()
    for medium in MEDIUM_PRIORITY:
        aliases = sorted(MEDIUM_ALIASES[medium], key=len, reverse=True)
        if any((alias in lowered for alias in aliases)):
            return medium
    return None

def _plausible(value):
    return 0 < value <= _MAX_PLAUSIBLE_DEPTH_M

def _make_range(low, high):
    low, high = (min(low, high), max(low, high))
    if high <= 0 or high > _MAX_PLAUSIBLE_DEPTH_M:
        return None
    if low < 0:
        low = 0.0
    return {'min_m': low, 'max_m': high}

def _extract_depth(text):
    candidates = []
    for match in _RANGE_WITH_CONTEXT.finditer(text):
        candidates.append((float(match.group(1)), float(match.group(2))))
    if candidates:
        return _make_range(*candidates[0])
    for match in _SINGLE_WITH_CONTEXT.finditer(text):
        value = float(match.group(1))
        if _plausible(value):
            return {'min_m': value, 'max_m': value}
    for match in _RANGE_BARE.finditer(text):
        return _make_range(float(match.group(1)), float(match.group(2)))
    for match in _SINGLE_TRAILING.finditer(text):
        value = float(match.group(1))
        if _plausible(value):
            return {'min_m': value, 'max_m': value}
    for match in _SINGLE_UNIT.finditer(text):
        prefix = text[max(0, match.start() - 6):match.start()]
        if any((word in prefix for word in ('水位', '厚', '高程', '桩号'))):
            continue
        value = float(match.group(1))
        if _plausible(value):
            return {'min_m': value, 'max_m': value}
    return None

def _extract_surface(text):
    for surface, keywords in _SURFACE_RULES:
        if any((keyword in text for keyword in keywords)):
            return surface
    return None

def _extract_interference(text):
    found = []
    lowered = text.lower()
    for interference, keywords in _INTERFERENCE_RULES:
        for keyword in keywords:
            position = lowered.find(keyword)
            if position < 0:
                continue
            if _is_negated(lowered, position):
                continue
            found.append(interference)
            break
    return found

def _extract_budget(text):
    if any((word in text for word in ('预算有限', '经费有限', '成本敏感', '低成本'))):
        return 'low'
    if any((word in text for word in ('预算充足', '不计成本', '高标准'))):
        return 'high'
    return None

def _extract_site_length(text):
    match = _SITE_LENGTH.search(text)
    if not match:
        return None
    value = float(match.group(1))
    return value if 10 <= value <= 100000 else None

def _extract_accuracy(text):
    match = re.search('(?:精度|分辨率|误差)[^，。；]{0,24}', text)
    return match.group(0).strip() if match else None

def extract_conditions(message):
    text = (message or '').strip()
    return {'target': _match_target(text), 'medium': _match_medium(text), 'depth': _extract_depth(text), 'surface': _extract_surface(text), 'interference': _extract_interference(text), 'budget': _extract_budget(text), 'site_length_m': _extract_site_length(text), 'accuracy': _extract_accuracy(text), 'free_text': text}

def build_questions(conditions):
    complete = bool(conditions['target'] and conditions['medium'] and conditions['depth'])
    questions = []
    if not conditions['target']:
        questions.append('要探测的目标是什么？（例如：地下管线/电缆、溶洞与脱空、含水层、污染羽、UXO、地层分层）')
    if not conditions['medium']:
        questions.append('目标所处的主要介质是什么？（黏土、粉土、砂土、填土、软土、灰岩、基岩）')
    if not conditions['depth']:
        questions.append('目标大致埋深或需要探查的深度范围是多少米？（例如 1~3 m、0~20 m）')
    if not conditions['surface'] and complete:
        questions.append('地表情况如何？（沥青/混凝土路面、农田草地、碎石覆盖、水域）——它决定耦合与接地方式')
    if not conditions['interference'] and complete:
        questions.append('场地内有哪些干扰？（钢筋/金属构筑物、电力线、交通振动、施工机械）——它决定方法取舍')
    return questions[:4]

def _design_depth(depth_range):
    return depth_range['max_m']

def max_depth_of(method, medium, target):
    return round(BASE_MAX_DEPTH[method][medium] * TARGET_DEPTH_FACTOR[method][target], 1)

def _depth_check(ratio, max_depth, depth):
    if ratio >= MARGIN_SATISFY:
        return f'满足（余量 {ratio:.1f}×）'
    if ratio >= MARGIN_CRITICAL:
        return f'临界（余量 {ratio:.1f}×）'
    if ratio >= MARGIN_FEASIBLE:
        return f'余量不足（{ratio:.2f}×）'
    return f'超限（{depth:g} m > {max_depth:g} m）'

def _split_constraints(conditions, method, ratio):
    blocking = []
    notes = []
    medium = conditions['medium']
    if ratio < MARGIN_CRITICAL:
        blocking.append(f'深度余量仅 {ratio:.2f}×，属理论上限，实际施工中易受衰减与噪声影响')
    medium_note = MEDIUM_CONSTRAINTS.get(method, {}).get(medium)
    if medium_note:
        blocking.append(medium_note)
    severe = SEVERE_INTERFERENCE.get(method, frozenset())
    for interference in conditions['interference']:
        note = INTERFERENCE_CONSTRAINTS.get(method, {}).get(interference)
        if not note:
            continue
        notes.append(f'{INTERFERENCE_CN[interference]}：{note}')
        if interference in severe:
            blocking.append(f'{INTERFERENCE_CN[interference]}：{note}')
    return (blocking, notes)

def _suitability(conditions, method, ratio, feasible, blocking):
    target = conditions['target']
    medium = conditions['medium']
    depth = _design_depth(conditions['depth'])
    base = BASE_SUITABILITY[target][method]
    if not feasible:
        return (N, f'最大探测深度 {max_depth_of(method, medium, target):g} m < 目标埋深 {depth:g} m，无法可靠覆盖目标')
    if base == N:
        specific = INAPPLICABLE_REASON.get((method, target))
        return (N, specific or f'该方法不测量{TARGET_CN[target]}所依赖的物性（{TARGET_CONTRAST[target]}），不宜采用')
    if blocking and base in (P, A):
        return (C, '；'.join(blocking))
    if blocking and base == S:
        return (S, '；'.join([_BASE_REASON[base], *blocking]))
    return (base, _BASE_REASON[base])

def _acquisition_and_resolution(conditions, method, max_depth):
    medium = conditions['medium']
    depth = _design_depth(conditions['depth'])
    if method == 'gpr':
        resolution_req = GPR_TARGET_RESOLUTION_M.get(conditions['target'])
        gpr = design_gpr(medium, depth, max_depth, resolution_req)
        return ({'天线中心频率': f"{gpr['antenna_mhz']:g} MHz", '记录时窗': f"{gpr['window_ns']:g} ns", '点距': f"{gpr['point_spacing_m']:g} m", '测线方向': '垂直目标走向，跨越已知异常布设'}, gpr['resolution_m'], gpr['note'], gpr['point_spacing_m'], None)
    if method == 'dc':
        dc = design_dc(depth)
        return ({'电极排列': '温纳（普查）+ 偶极-偶极（异常加密）', '电极距': f"{dc['spacing_m']:g} m", '排列长度': f"{dc['array_length_m']:g} m（{dc['channels']} 道）", '接地要求': '高阻/碎石地表需浇水或换位，逐点记录接地电阻'}, dc['resolution_m'], dc['note'], dc['spacing_m'], dc['array_length_m'])
    if method == 'surface_wave':
        sw = design_surface_wave(depth)
        return ({'道间距': f"{sw['spacing_m']:g} m", '排列长度': f"{sw['array_length_m']:g} m（{sw['channels']} 道）", '震源': '锤击或落重，多次叠加', '环境': '避开强振动时段，记录背景噪声'}, sw['resolution_m'], sw['note'], sw['spacing_m'], sw['array_length_m'])
    if method == 'refraction':
        refr = design_refraction(depth)
        return ({'道间距': f"{refr['spacing_m']:g} m", '排列长度': f"{refr['array_length_m']:g} m（{refr['channels']} 道）", '震源': '锤击或落重，多次叠加；深部目标可加大锤重', '环境': '避开交通振动时段，记录背景噪声'}, refr['resolution_m'], refr['note'], refr['spacing_m'], refr['array_length_m'])
    if method == 'magnetic':
        mag = design_magnetic(depth)
        return ({'线距': f"{mag['line_spacing_m']:g} m", '点距': f"{mag['station_spacing_m']:g} m", '高度': '探头离地约 0.5 m，必要时做多高度测量', '校正': '日变改正 + 静态改正，避开车辆与铁质物体'}, mag['resolution_m'], mag['note'], mag['station_spacing_m'], None)
    if method == 'fdem':
        fdem = design_fdem(depth)
        return ({'线圈距': f"{fdem['line_spacing_m']:g} m", '频段': fdem['note'].split('；')[0], '点距': f"{fdem['station_spacing_m']:g} m", '姿态': '保持线圈姿态与离地高度一致，先做零点校正'}, fdem['resolution_m'], fdem['note'], fdem['station_spacing_m'], None)
    if method == 'tem':
        tem = design_tem(depth)
        return ({'回线边长': f"{tem['line_spacing_m']:g} m", '测点距': f"{tem['station_spacing_m']:g} m", '记录': '关断后测二次场衰减，晚时间道对应深部', '校正': '避开电力线与管线，先做背景噪声测量'}, tem['resolution_m'], tem['note'], tem['station_spacing_m'], None)
    das = design_das(depth)
    return ({'通道间距': f"{das['channel_spacing_m']:g} m", '光缆长度': f"≥{das['borehole_depth_m']:g} m（钻孔或既有通信光缆）", '解调': '需专业解调仪与相位解缠处理'}, das['resolution_m'], das['note'], das['channel_spacing_m'], None)

def _limitations(conditions, method, extra_notes):
    target = conditions['target']
    medium = conditions['medium']
    items = []
    extra = TARGET_EXTRA_LIMITATIONS.get(target, {}).get(method)
    if extra:
        items.append(extra)
    medium_note = MEDIUM_CONSTRAINTS.get(method, {}).get(medium)
    if medium_note:
        items.append(medium_note)
    items.extend(extra_notes)
    items.extend(METHOD_META[method]['base_limitations'])
    seen = set()
    unique = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:6]

def _promotion_tier(method, target):
    base = BASE_SUITABILITY[target][method]
    return {P: 0, A: 1, S: 2}.get(base, 3)

def _promote_primary(methods, target, warnings):
    primary = [m for m in METHOD_ORDER if methods[m]['suitability'] == P]
    if primary:
        return primary
    applicable = [m for m in METHOD_ORDER if methods[m]['suitability'] == A]
    if applicable:
        applicable.sort(key=lambda m: (-methods[m]['depth_margin'], _promotion_tier(m, target)))
        best = applicable[0]
        warnings.append(f"当前埋深下没有方法判为“首选”，按深度余量改以 {methods[best]['method_cn']}（余量 {methods[best]['depth_margin']:.2f}×）为主方法")
        return [best]
    constrained = [m for m in METHOD_ORDER if methods[m]['suitability'] == C]
    if constrained:
        names = '、'.join((methods[m]['method_cn'] for m in constrained[:3]))
        warnings.append(f'八种演示方法在当前条件下均受限（{names}等），没有可直接推荐的主方法，建议扩展方法范围（反射/微动/重力/测井等）或钻探为主、分段设计')
    else:
        warnings.append('当前条件下没有可行方法，建议改用钻探为主或分段设计')
    return []
DEFAULT_SITE_LENGTH_M = 200.0
FLANK_LINES = 2
CROSS_LINE_TARGETS = ('karst', 'utility', 'site_investigation')
CROSS_LINE_SPACING_M = 30.0
CROSS_LINE_LENGTH_M = 60.0
COST_BAND_LOW = 12.0
COST_BAND_MEDIUM = 35.0

def build_design(method, assessment, site_length_m, depth_m, target):
    if method is None or assessment is None:
        return {'primary_method': None, 'main_line_length_m': 0.0, 'line_count': 0, 'cross_line_spacing_m': None, 'total_line_km': 0.0, 'station_count': None, 'relative_cost_index': 0.0, 'cost_band': '未评估', 'basis': ['尚未确定主方法，暂不给出外业布置']}
    main_length = float(site_length_m or DEFAULT_SITE_LENGTH_M)
    line_count = 1 + FLANK_LINES
    basis = [f'主测线沿勘查对象走向布置，长度按场地可布设长度取 {main_length:g} m', f'主测线两侧各布 1 条平行测线，合计 {line_count} 条']
    cross_spacing = None
    total_length = main_length * line_count
    if target in CROSS_LINE_TARGETS:
        cross_spacing = CROSS_LINE_SPACING_M
        cross_count = max(1, round(main_length / cross_spacing))
        total_length += cross_count * CROSS_LINE_LENGTH_M
        basis.append(f'{TARGET_CN[target]}需要平面控制，每 {cross_spacing:g} m 加 1 条 {CROSS_LINE_LENGTH_M:g} m 横测线，共 {cross_count} 条')
    station_count = None
    spacing = assessment['station_spacing_m']
    if spacing:
        station_count = round(total_length / spacing)
        basis.append(f'按点距/电极距 {spacing:g} m 计，测点总数约 {station_count} 点')
    cost_index = METHOD_META[method]['cost_index'] * total_length / 100.0
    if cost_index <= COST_BAND_LOW:
        band = '低'
    elif cost_index <= COST_BAND_MEDIUM:
        band = '中'
    else:
        band = '高'
    basis.append(f"相对成本指数 = {METHOD_META[method]['cost_index']:g}（每 100 m，GPR=1） × {total_length / 100.0:.1f} 个百 m = {cost_index:.1f}，属{band}成本档")
    return {'primary_method': method, 'main_line_length_m': round(main_length, 1), 'line_count': line_count, 'cross_line_spacing_m': cross_spacing, 'total_line_km': round(total_length / 1000.0, 3), 'station_count': station_count, 'relative_cost_index': round(cost_index, 1), 'cost_band': band, 'basis': basis}

def assess(conditions):
    if not (conditions['target'] and conditions['medium'] and conditions['depth']):
        missing = []
        if not conditions['target']:
            missing.append('探测目标')
        if not conditions['medium']:
            missing.append('主要介质')
        if not conditions['depth']:
            missing.append('目标埋深')
        raise ValueError('场地条件不完整，缺少：' + '、'.join(missing))
    target = conditions['target']
    medium = conditions['medium']
    depth = _design_depth(conditions['depth'])
    methods = {}
    warnings = []
    for method in METHOD_ORDER:
        max_depth = max_depth_of(method, medium, target)
        ratio = round(max_depth / depth, 3)
        feasible = ratio >= MARGIN_FEASIBLE
        blocking, notes = _split_constraints(conditions, method, ratio)
        suitability, reason = _suitability(conditions, method, ratio, feasible, blocking)
        params, resolution, resolution_basis, spacing, array_length = _acquisition_and_resolution(conditions, method, max_depth)
        meta = METHOD_META[method]
        methods[method] = {'method': method, 'method_cn': METHOD_CN[method], 'max_depth_m': max_depth, 'depth_margin': ratio, 'depth_check': _depth_check(ratio, max_depth, depth), 'feasible': feasible, 'suitability': suitability, 'suitability_reason': reason, 'vertical_resolution_m': resolution, 'resolution_basis': resolution_basis, 'station_spacing_m': spacing, 'array_length_m': array_length, 'relative_cost': meta['relative_cost'], 'cost_index': meta['cost_index'], 'acquisition': params, 'physics_basis': meta['physics_basis'], 'deployment_requirement': meta['deployment_requirement'], 'limitations': _limitations(conditions, method, blocking + notes), 'interference_notes': notes}
    primary = _promote_primary(methods, target, warnings)
    support = [method for method in METHOD_ORDER if method not in primary and methods[method]['suitability'] in (A, S, C)]
    infeasible = [method for method in METHOD_ORDER if not methods[method]['feasible']]
    for method in infeasible:
        warnings.append(f"{METHOD_CN[method]} 最大探测深度 {methods[method]['max_depth_m']:g} m < 目标埋深 {depth:g} m，无法覆盖目标")
    if methods['das']['feasible'] and methods['das']['suitability'] != N:
        warnings.append('DAS 需要钻孔内光缆或既有通信光缆，场地不具备时不能作为独立方法')
    if target in ('plume', 'aquifer'):
        warnings.append('磁法对污染羽/含水层没有直接物性响应，只能用于排查铁磁干扰或管线')
    if medium == 'fill':
        warnings.append('填土中常含建筑垃圾与钢筋，GPR 与 DC 都可能出现强干扰，需先做试验剖面')
    design_method = primary[0] if primary else None
    design = build_design(design_method, methods[design_method] if design_method else None, site_length_m=conditions.get('site_length_m'), depth_m=depth, target=target)
    return {'target_cn': TARGET_CN[target], 'medium_cn': MEDIUM_CN[medium], 'design_depth_m': depth, 'depth_range': f"{conditions['depth']['max_m']:g} m" if conditions['depth']['min_m'] == conditions['depth']['max_m'] else f"{conditions['depth']['min_m']:g}~{conditions['depth']['max_m']:g} m", 'methods': methods, 'method_order': list(METHOD_ORDER), 'recommended_primary': primary, 'recommended_support': support, 'infeasible': infeasible, 'design': design, 'warnings': warnings, 'target_contrast': TARGET_CONTRAST[target], 'target_note': TARGET_NOTES[target], 'conditions': conditions, 'conditions_view': {'target': TARGET_CN.get(conditions['target']), 'medium': MEDIUM_CN.get(conditions['medium']), 'depth': None if not conditions['depth'] else f"{conditions['depth']['max_m']:g} m" if conditions['depth']['min_m'] == conditions['depth']['max_m'] else f"{conditions['depth']['min_m']:g}~{conditions['depth']['max_m']:g} m", 'surface': SURFACE_CN.get(conditions['surface']) if conditions['surface'] else None, 'interference': '、'.join((INTERFERENCE_CN[i] for i in conditions['interference'])) or None, 'budget': BUDGET_CN.get(conditions['budget']) if conditions['budget'] else None, 'site_length': f"{conditions['site_length_m']:g} m" if conditions['site_length_m'] else None}, 'disclaimer': DISCLAIMER}

def build_prompt_input(query, bundle):
    lines = [f'方法代码 | 方法 | 最大深度m | 深度余量 | 深度校核 | 适用性 | 垂向分辨率m | 成本 | 关键限制']
    lines.append('---|---|---|---|---|---|---|---|---')
    for method in METHOD_ORDER:
        item = bundle['methods'][method]
        resolution = f"{item['vertical_resolution_m']:g}" if item['vertical_resolution_m'] is not None else '无垂向分辨'
        limit = item['limitations'][0] if item['limitations'] else '-'
        lines.append(f"{method} | {item['method_cn']} | {item['max_depth_m']:g} | {item['depth_margin']:.2f}× | {item['depth_check']} | {item['suitability']} | {resolution} | {item['relative_cost']} | {limit}")
    table = '\n'.join(lines)
    view = bundle['conditions_view']
    conditions_text = '\n'.join([f"- 探测目标：{view.get('target') or '未知'}", f"- 主要介质：{view.get('medium') or '未知'}", f"- 目标埋深：{bundle['depth_range']}", f"- 地表条件：{view.get('surface') or '未说明'}", f"- 场地干扰：{view.get('interference') or '未说明'}", f"- 预算约束：{view.get('budget') or '未说明'}", f"- 场地长度：{view.get('site_length') or '未说明'}"])
    primary = '、'.join(bundle['recommended_primary']) or '无'
    support = '、'.join(bundle['recommended_support']) or '无'
    infeasible = '、'.join(bundle['infeasible']) or '无'
    design_text = '\n'.join((f'- {line}' for line in bundle['design']['basis'])) or '- 未生成'
    return f"## 用户场景描述\n{query}\n\n## 已解析的场地条件\n{conditions_text}\n\n## 评估表（唯一事实来源，数值不得改动）\n{table}\n\n## 计算器结论\n- 推荐主方法：{primary}\n- 可作为辅助：{support}\n- 深度不可行：{infeasible}\n- 目标物性对比：{bundle['target_contrast']}\n- 目标解释提示：{bundle['target_note']}\n- 系统提示：{'；'.join(bundle['warnings']) or '无'}\n\n## 外业设计草案（可引用，不得改动数值）\n{design_text}"

def merge_conditions(previous, update):
    merged = dict(previous)
    for name in ('target', 'medium', 'depth', 'surface', 'budget', 'site_length_m', 'accuracy'):
        value = update.get(name)
        if value is not None and value != '':
            merged[name] = value
    if update.get('interference'):
        merged['interference'] = list(update['interference'])
    merged['free_text'] = update.get('free_text')
    return merged

def render_clarification(conditions, questions):
    known = []
    if conditions.get('target'):
        known.append(f"探测目标：{TARGET_CN[conditions['target']]}")
    if conditions.get('medium'):
        known.append(f"主要介质：{MEDIUM_CN[conditions['medium']]}")
    if conditions.get('depth'):
        depth = conditions['depth']
        text = f"{depth['max_m']:g} m" if depth['min_m'] == depth['max_m'] else f"{depth['min_m']:g}~{depth['max_m']:g} m"
        known.append(f'目标埋深：{text}')
    known_text = '、'.join(known) if known else '暂无'
    lines = ['# 需要补充信息', '', '我是「工程物探勘察方案推荐」助手：从八种工程物探方法（GPR／直流电阻率／面波／地震折射／磁法／FDEM／TEM／DAS）里比选方案，按物理关系反算采集参数，并估算外业工作量。', '', f'目前已确认：{known_text}。还缺关键字段，无法给出可靠方案——物探方法的选择高度依赖目标物性差异与埋深，缺项时给出的方案容易变成「按名称套方法」。', '', '## 请补充', '']
    lines.extend((f'{index}. {question}' for index, question in enumerate(questions, start=1)))
    lines.extend(['', '## 补齐后我会做什么', '', '1. 用八种方法的深度-分辨率-成本评估表逐项校核；', '2. 按物理关系反算排列长度、电极距、天线频率等采集参数；', '3. 生成方案并用规则校验器自检，冲突时自动修正。'])
    return '\n'.join(lines) + '\n'

def main(query: str, prev_conditions: str='') -> dict:
    update = extract_conditions(query)
    conditions = update
    if prev_conditions:
        try:
            previous = json.loads(prev_conditions)
        except (json.JSONDecodeError, TypeError):
            previous = {}
        if isinstance(previous, dict) and previous:
            conditions = merge_conditions(previous, update)
    if not (conditions['target'] and conditions['medium'] and conditions['depth']):
        questions = build_questions(conditions)
        return {'status': 'need_more_info', 'assess_json': '', 'prompt_input': '', 'conditions_json': json.dumps(conditions, ensure_ascii=False), 'clarification_md': render_clarification(conditions, questions)}
    bundle = assess(conditions)
    bundle['status'] = 'ok'
    bundle['questions'] = []
    return {'status': 'ok', 'assess_json': json.dumps(bundle, ensure_ascii=False), 'prompt_input': build_prompt_input(query, bundle), 'conditions_json': json.dumps(conditions, ensure_ascii=False), 'clarification_md': ''}
BUILD = '2026-11-17.2'
