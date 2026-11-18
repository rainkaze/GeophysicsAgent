"""物探方法的定量关系：由目标深度反算采集参数与理论分辨率。

这些是课程中的**量级规则**（教材/课件层面的经验关系），用途是给出"可核对的设计起点"：
- GPR：``v = c/√εr``，``λ = v/f``，垂向分辨率约 ``λ/4``，记录时窗 ``t = 2d/v``；
- DC：有效探测深度约为排列长度的 0.2–0.3 倍，此处取 0.25；
- 面波：排列长度约为目标深度的 2–3 倍，此处取 2.5；
- 磁法：无垂向分辨能力，测网密度按目标埋深取经验值；
- FDEM：按目标深度选择线圈距与频段，垂向分辨率约 0.3–0.5 倍勘探深度；
- DAS：通道间距约 1 m，深度由钻孔或既有光缆长度决定。

所有返回值都带 ``note`` 字段说明推导方式，便于在方案里逐条追溯。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from geophysics_agent.domain.enums import Medium

#: 电磁波在真空中的速度（m/ns）
LIGHT_SPEED_M_PER_NS = 0.3

#: 各介质的相对介电常数（课程量级取值）
RELATIVE_PERMITTIVITY: dict[Medium, float] = {
    Medium.CLAY: 12.0,
    Medium.SILT: 8.0,
    Medium.SAND: 6.0,
    Medium.FILL: 8.0,
    Medium.LIMESTONE: 7.0,
    Medium.BEDROCK: 7.0,
    Medium.SOFT_SOIL: 15.0,
}

#: 各介质的电导率量级（mS/m），用于估算 GPR 趋肤深度
CONDUCTIVITY_MS_PER_M: dict[Medium, float] = {
    Medium.CLAY: 60.0,
    Medium.SILT: 30.0,
    Medium.SAND: 8.0,
    Medium.FILL: 25.0,
    Medium.LIMESTONE: 2.0,
    Medium.BEDROCK: 5.0,
    Medium.SOFT_SOIL: 80.0,
}

#: 可选的 GPR 天线频率（MHz），从高到低
GPR_ANTENNAS_MHZ: tuple[float, ...] = (1000.0, 500.0, 250.0, 100.0, 50.0)
#: 深度经验值对应的基准频率
GPR_BASE_FREQ_MHZ = 100.0

#: DC 有效深度 / 排列长度
DC_DEPTH_TO_ARRAY = 0.25
#: 面波排列长度 / 目标深度
SURFACE_WAVE_ARRAY_TO_DEPTH = 2.5


@dataclass(frozen=True)
class GprDesign:
    """GPR 采集设计。"""

    antenna_mhz: float
    reachable_depth_m: float
    resolution_m: float
    window_ns: float
    point_spacing_m: float
    note: str


@dataclass(frozen=True)
class ArrayDesign:
    """阵列类方法（DC / 面波）的采集设计。"""

    array_length_m: float
    spacing_m: float
    channels: int
    resolution_m: float
    note: str


@dataclass(frozen=True)
class GridDesign:
    """测网类方法（磁法 / FDEM）的采集设计。"""

    line_spacing_m: float
    station_spacing_m: float
    resolution_m: float | None
    note: str


@dataclass(frozen=True)
class FiberDesign:
    """DAS 光纤布设设计。"""

    channel_spacing_m: float
    borehole_depth_m: float
    resolution_m: float
    note: str


def gpr_velocity_m_per_ns(medium: Medium) -> float:
    """电磁波在介质中的传播速度（m/ns）。"""
    return LIGHT_SPEED_M_PER_NS / math.sqrt(RELATIVE_PERMITTIVITY[medium])


def gpr_wavelength_m(medium: Medium, frequency_mhz: float) -> float:
    """介质中的电磁波波长（m）。"""
    return gpr_velocity_m_per_ns(medium) * 1000.0 / frequency_mhz


def _reachable_depth(base_depth_m: float, frequency_mhz: float) -> float:
    """按经验关系把基准频率下的可达深度换算到目标频率。

    穿透能力随频率升高而下降，经验上按 ``√(f_base/f)`` 缩放。
    """
    return base_depth_m * math.sqrt(GPR_BASE_FREQ_MHZ / frequency_mhz)


def design_gpr(
    medium: Medium,
    required_depth_m: float,
    base_depth_m: float,
    min_resolution_m: float | None = None,
) -> GprDesign:
    """按目标深度与分辨率选择天线频率，并给出分辨率、时窗与点距。

    小目标（管线/UXO）需要更高频率以获得足够分辨率；当"能分辨目标的频率"
    覆盖不了 1.3× 目标深度时，优先保分辨率（否则小目标根本分辨不出），
    并在 note 里如实标注"深度覆盖可能不足"。
    """
    safety = 1.3
    velocity = gpr_velocity_m_per_ns(medium)

    def resolution_of(frequency_mhz: float) -> float:
        return gpr_wavelength_m(medium, frequency_mhz) / 4.0

    chosen = GPR_ANTENNAS_MHZ[-1]
    # 第一遍：同时满足深度覆盖 + 分辨率要求（若有）的最高频率
    for frequency in GPR_ANTENNAS_MHZ:
        reachable = _reachable_depth(base_depth_m, frequency)
        ok_resolution = min_resolution_m is None or resolution_of(frequency) <= min_resolution_m
        if reachable >= required_depth_m * safety and ok_resolution:
            chosen = frequency
            break

    # 第二遍：小目标的分辨率要求与深度冲突时，选"能分辨目标的最低频率"（尽量保深度）
    resolution_limited = False
    if min_resolution_m is not None and resolution_of(chosen) > min_resolution_m:
        for frequency in reversed(GPR_ANTENNAS_MHZ):  # 低→高
            if resolution_of(frequency) <= min_resolution_m:
                chosen = frequency
                resolution_limited = True
                break

    reachable = _reachable_depth(base_depth_m, chosen)
    wavelength = gpr_wavelength_m(medium, chosen)
    resolution = wavelength / 4.0
    window = 2.0 * required_depth_m * safety / velocity
    spacing = min(0.5, max(0.05, round(resolution / 4.0, 2)))
    note = (
        f"按 εr={RELATIVE_PERMITTIVITY[medium]:g} 得 v={velocity:.3f} m/ns，"
        f"选 {chosen:g} MHz（经验可达 {reachable:.1f} m，需覆盖 1.3×目标深度）；"
        f"λ={wavelength:.2f} m，分辨率按 λ/4 取 {resolution:.2f} m；"
        f"时窗按 t=2d/v 取 {window:.0f} ns"
    )
    if resolution_limited:
        note += f"；受小目标尺寸限制，{chosen:g} MHz 的深度覆盖可能不足，需低频复核或加密点距"
    return GprDesign(
        chosen, round(reachable, 1), round(resolution, 2), round(window, 0), spacing, note
    )


def design_dc(depth_m: float, electrodes: int = 48) -> ArrayDesign:
    """按 0.25 倍关系反算 DC 排列长度与电极距。"""
    needed = depth_m / DC_DEPTH_TO_ARRAY
    ladder = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0, 15.0, 20.0)
    spacing = ladder[-1]
    for candidate in ladder:
        if candidate * (electrodes - 1) >= needed:
            spacing = candidate
            break
    array_length = spacing * (electrodes - 1)
    resolution = 0.15 * depth_m
    note = (
        f"有效深度≈0.25×排列长度，目标 {depth_m:g} m 需排列长约 {needed:.0f} m；"
        f"{electrodes} 道电极取电极距 {spacing:g} m，实际排列长 {array_length:g} m；"
        f"垂向分辨率按 0.15×深度估约 {resolution:.1f} m"
    )
    return ArrayDesign(round(array_length, 1), spacing, electrodes, round(resolution, 1), note)


def design_surface_wave(depth_m: float, channels: int = 24) -> ArrayDesign:
    """按 2.5 倍关系反算面波排列长度与道间距。"""
    needed = depth_m * SURFACE_WAVE_ARRAY_TO_DEPTH
    spacing = max(1.0, math.ceil(needed / (channels - 1) * 2.0) / 2.0)
    array_length = spacing * (channels - 1)
    resolution = 0.2 * depth_m
    note = (
        f"排列长度取 2.5×目标深度≈{needed:.0f} m；{channels} 道取道间距 {spacing:g} m，"
        f"实际排列长 {array_length:g} m；分层分辨率按 0.2×深度估约 {resolution:.1f} m"
    )
    return ArrayDesign(round(array_length, 1), spacing, channels, round(resolution, 1), note)


def design_refraction(depth_m: float, channels: int = 24) -> ArrayDesign:
    """按 4 倍关系反算折射排列长度与道间距（有效深度≈0.25×排列长度）。"""
    needed = depth_m * 4.0
    spacing = max(1.0, math.ceil(needed / (channels - 1) * 2.0) / 2.0)
    array_length = spacing * (channels - 1)
    resolution = 0.2 * depth_m
    note = (
        f"有效深度≈0.25×排列长度，目标 {depth_m:g} m 需排列长约 {needed:.0f} m；"
        f"{channels} 道取道间距 {spacing:g} m，实际排列长 {array_length:g} m；"
        f"分层分辨率按 0.2×深度估约 {resolution:.1f} m"
    )
    return ArrayDesign(round(array_length, 1), spacing, channels, round(resolution, 1), note)


def design_magnetic(depth_m: float) -> GridDesign:
    """磁法测网密度：线距≈目标埋深，点距≈埋深一半。"""
    line_spacing = max(1.0, round(depth_m, 1))
    station_spacing = max(0.5, round(depth_m / 2.0, 1))
    return GridDesign(
        line_spacing,
        station_spacing,
        None,
        "磁法无垂向分辨能力，只能平面定位；线距按目标埋深的 1 倍、点距按 0.5 倍布置",
    )


def design_fdem(depth_m: float) -> GridDesign:
    """FDEM 按目标深度选择线圈距与频段。"""
    if depth_m <= 6.0:
        coil, band = 3.66, "高频段（约 9.8 kHz）"
    elif depth_m <= 15.0:
        coil, band = 10.0, "中频段（约 1.6–6.4 kHz）"
    else:
        coil, band = 20.0, "低频段（约 0.4–1.6 kHz）"
    station = max(1.0, round(depth_m / 2.0, 1))
    resolution = round(0.4 * depth_m, 1)
    return GridDesign(
        coil,
        station,
        resolution,
        f"按目标 {depth_m:g} m 选线圈距 {coil:g} m、{band}；扩散场垂向分辨率约 0.4×深度≈{resolution:g} m",
    )


def design_tem(depth_m: float) -> GridDesign:
    """TEM 按目标深度建议回线边长与测点距。"""
    loop = max(10.0, round(depth_m * 0.5, 0))
    station = max(5.0, round(depth_m * 0.5, 0))
    resolution = round(0.3 * depth_m, 1)
    return GridDesign(
        loop,
        station,
        resolution,
        f"按目标 {depth_m:g} m 建议回线边长约 {loop:g} m、测点距 {station:g} m；"
        f"扩散场垂向分辨率约 0.3×深度≈{resolution:g} m，深部探测需增大发射磁矩并延长记录时间",
    )


def design_das(depth_m: float) -> FiberDesign:
    """DAS 通道间距与钻孔深度。"""
    borehole = depth_m + 10.0
    return FiberDesign(
        1.0,
        round(borehole, 1),
        1.0,
        f"通道间距 1 m；钻孔或既有光缆长度需覆盖目标深度并留 10 m 余量，建议 ≥{borehole:g} m",
    )
