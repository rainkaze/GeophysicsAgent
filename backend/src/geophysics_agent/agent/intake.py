"""条件抽取：把自然语言场景解析成 ``SiteConditions``。

这里刻意使用**确定性规则**而不是让模型抽取，原因是：
- 字段有限、模式稳定，规则可解释、可单测、零成本、零延迟；
- 漏抽只影响"是否需要澄清"，不会产生错误的数值；
- 多轮对话时可以把新抽取结果合并进会话记忆（``SiteConditions.merge``）。
"""

from __future__ import annotations

import re

from geophysics_agent.analysis.tables import (
    MEDIUM_ALIASES,
    MEDIUM_PRIORITY,
    TARGET_ALIASES,
    TARGET_PRIORITY,
)
from geophysics_agent.domain.conditions import DepthRange, SiteConditions
from geophysics_agent.domain.enums import Budget, Interference, Medium, Surface, Target

#: 埋深必须落在合理范围内，避免把页码、桩号当成埋深
_MAX_PLAUSIBLE_DEPTH_M = 300.0

_RANGE_WITH_CONTEXT = re.compile(
    r"(?:埋深|深度|深约|埋藏深度|目标层深度)[^\d]{0,8}"
    r"(\d+(?:\.\d+)?)\s*(?:~|～|-|—|到|至)\s*(\d+(?:\.\d+)?)"
)
_SINGLE_WITH_CONTEXT = re.compile(
    r"(?:埋深|深度|深约|埋藏深度)[^\d]{0,8}(\d+(?:\.\d+)?)\s*(?:m|米)?"
)
_RANGE_BARE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:~|～|-|—|到|至)\s*(\d+(?:\.\d+)?)\s*(?:m|米)")
_SINGLE_TRAILING = re.compile(r"(\d+(?:\.\d+)?)\s*(?:m|米)\s*(?:埋深|深度|以深|以内|左右|深)")
_SINGLE_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:m|米)")
_SITE_LENGTH = re.compile(r"(?:场地|测线|路基)[^，。；]{0,6}?(\d+(?:\.\d+)?)\s*(?:m|米)")

_INTERFERENCE_RULES: tuple[tuple[Interference, tuple[str, ...]], ...] = (
    (Interference.REBAR, ("钢筋", "钢筋混凝土", "金属设施", "金属构件")),
    (Interference.POWERLINE, ("电力线", "高压", "kv", "千伏", "输电线")),
    (Interference.TRAFFIC, ("交通", "车辆", "车流", "行车")),
    (Interference.MACHINERY, ("施工机械", "机械作业", "施工机具", "钻机")),
    (Interference.FENCE, ("围栏", "铁栅", "围挡", "栅栏")),
    (Interference.TERRAIN, ("地形起伏", "起伏较大", "山地", "陡坡", "地形复杂")),
    (Interference.VIBRATION, ("振动", "震动", "轻微交通振动", "持续振动")),
)

_SURFACE_RULES: tuple[tuple[Surface, tuple[str, ...]], ...] = (
    (Surface.PAVED, ("沥青", "混凝土", "水泥", "硬化路面", "路面")),
    (Surface.GRAVEL, ("碎石", "砾石覆盖", "碎石覆盖")),
    (Surface.WATER, ("水域", "河道", "湖面", "海上", "水面")),
    (Surface.GRASS, ("农田", "草地", "绿化带", "空地", "耕地")),
)

#: 否定词：命中关键词前若出现这些词，说明用户是在**排除**该条件
_NEGATION_WORDS = ("无", "没有", "不存在", "不具备", "未发现", "少见", "少有")


def _is_negated(text: str, index: int, window: int = 6) -> bool:
    """判断关键词是否处于否定语境，例如"无重要金属设施"。"""
    prefix = text[max(0, index - window) : index]
    return any(word in prefix for word in _NEGATION_WORDS)


def _match_target(text: str) -> Target | None:
    """按既定优先级匹配目标，优先级用于消除"地下水污染羽"这类歧义。"""
    lowered = text.lower()
    for target in TARGET_PRIORITY:
        aliases = sorted(TARGET_ALIASES[target], key=len, reverse=True)
        if any(alias in lowered for alias in aliases):
            return target
    return None


def _match_medium(text: str) -> Medium | None:
    lowered = text.lower()
    for medium in MEDIUM_PRIORITY:
        aliases = sorted(MEDIUM_ALIASES[medium], key=len, reverse=True)
        if any(alias in lowered for alias in aliases):
            return medium
    return None


def _plausible(value: float) -> bool:
    return 0 < value <= _MAX_PLAUSIBLE_DEPTH_M


def _extract_depth(text: str) -> DepthRange | None:
    """按"带上下文的范围 → 带上下文的单值 → 裸范围 → 带单位的单值"四级回退。"""
    candidates: list[tuple[float, float]] = []

    for match in _RANGE_WITH_CONTEXT.finditer(text):
        candidates.append((float(match.group(1)), float(match.group(2))))
    if candidates:
        return _make_range(*candidates[0])

    for match in _SINGLE_WITH_CONTEXT.finditer(text):
        value = float(match.group(1))
        if _plausible(value):
            return DepthRange(min_m=value, max_m=value)

    for match in _RANGE_BARE.finditer(text):
        return _make_range(float(match.group(1)), float(match.group(2)))

    for match in _SINGLE_TRAILING.finditer(text):
        value = float(match.group(1))
        if _plausible(value):
            return DepthRange(min_m=value, max_m=value)

    # 兜底：任何带 m/米 的数字，但排除"水位""厚度"这类上下文
    for match in _SINGLE_UNIT.finditer(text):
        prefix = text[max(0, match.start() - 6) : match.start()]
        if any(word in prefix for word in ("水位", "厚", "高程", "桩号")):
            continue
        value = float(match.group(1))
        if _plausible(value):
            return DepthRange(min_m=value, max_m=value)
    return None


def _make_range(low: float, high: float) -> DepthRange | None:
    low, high = min(low, high), max(low, high)
    if high <= 0 or high > _MAX_PLAUSIBLE_DEPTH_M:
        return None
    if low < 0:
        low = 0.0
    return DepthRange(min_m=low, max_m=high)


def _extract_surface(text: str) -> Surface | None:
    for surface, keywords in _SURFACE_RULES:
        if any(keyword in text for keyword in keywords):
            return surface
    return None


def _extract_interference(text: str) -> list[Interference]:
    """抽取干扰，并跳过处于否定语境的关键词。"""
    found: list[Interference] = []
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


def _extract_budget(text: str) -> Budget | None:
    if any(word in text for word in ("预算有限", "经费有限", "成本敏感", "低成本")):
        return Budget.LOW
    if any(word in text for word in ("预算充足", "不计成本", "高标准")):
        return Budget.HIGH
    return None


def _extract_site_length(text: str) -> float | None:
    match = _SITE_LENGTH.search(text)
    if not match:
        return None
    value = float(match.group(1))
    return value if 10 <= value <= 100_000 else None


def _extract_accuracy(text: str) -> str | None:
    match = re.search(r"(?:精度|分辨率|误差)[^，。；]{0,24}", text)
    return match.group(0).strip() if match else None


def extract_conditions(message: str) -> SiteConditions:
    """从一段自然语言中抽取场地条件；未提及的字段保持 ``None``。"""
    text = message.strip()
    return SiteConditions(
        target=_match_target(text),
        medium=_match_medium(text),
        depth=_extract_depth(text),
        surface=_extract_surface(text),
        interference=_extract_interference(text),
        budget=_extract_budget(text),
        site_length_m=_extract_site_length(text),
        accuracy=_extract_accuracy(text),
        free_text=text,
    )


def build_questions(conditions: SiteConditions) -> list[str]:
    """针对缺失字段生成具体、可回答的追问。"""
    questions: list[str] = []
    if conditions.target is None:
        questions.append(
            "要探测的目标是什么？（例如：地下管线/电缆、溶洞与脱空、含水层、污染羽、UXO、地层分层）"
        )
    if conditions.medium is None:
        questions.append("目标所处的主要介质是什么？（黏土、粉土、砂土、填土、软土、灰岩、基岩）")
    if conditions.depth is None:
        questions.append("目标大致埋深或需要探查的深度范围是多少米？（例如 1~3 m、0~20 m）")
    if conditions.surface is None and conditions.is_complete():
        questions.append(
            "地表情况如何？（沥青/混凝土路面、农田草地、碎石覆盖、水域）——它决定耦合与接地方式"
        )
    if not conditions.interference and conditions.is_complete():
        questions.append(
            "场地内有哪些干扰？（钢筋/金属构筑物、电力线、交通振动、施工机械）——它决定方法取舍"
        )
    return questions[:4]
