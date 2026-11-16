"""场地条件模型：agent 的"目标状态"，也是会话记忆的最小单元。

设计要求：
- 每个字段都可有可无；缺失即"待澄清"，不猜测。
- 支持会话内增量合并（用户补充或修正某个字段时，只覆盖该字段）。
- 明确区分"设计埋深"（取范围上限，最不利）与"浅端埋深"（用于分辨率校核）。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from geophysics_agent.domain.enums import Budget, Interference, Medium, Surface, Target

CRITICAL_FIELDS: tuple[str, ...] = ("target", "medium", "depth")


class DepthRange(BaseModel):
    """目标埋深区间（m）。范围输入取上限作为设计埋深。"""

    model_config = ConfigDict(frozen=True)

    min_m: float = Field(ge=0, description="浅端埋深")
    max_m: float = Field(gt=0, description="深端埋深，用作设计埋深")

    def __str__(self) -> str:
        if self.min_m == self.max_m:
            return f"{self.max_m:g} m"
        return f"{self.min_m:g}~{self.max_m:g} m"

    @property
    def design_depth_m(self) -> float:
        """最不利校核深度：取深端。"""
        return self.max_m

    @property
    def is_ranged(self) -> bool:
        return self.min_m != self.max_m

    @model_validator(mode="after")
    def _check_order(self) -> DepthRange:
        if self.max_m < self.min_m:
            raise ValueError("埋深上限不得小于下限")
        return self


class SiteConditions(BaseModel):
    """从用户自然语言中抽取出的场地条件。"""

    model_config = ConfigDict(extra="forbid")

    target: Target | None = None
    medium: Medium | None = None
    depth: DepthRange | None = None
    surface: Surface | None = None
    interference: list[Interference] = Field(default_factory=list)
    budget: Budget | None = None
    site_length_m: float | None = Field(default=None, gt=0, description="可布设测线的场地长度")
    accuracy: str | None = Field(default=None, description="用户提出的精度/分辨率要求原文")
    free_text: str | None = Field(default=None, description="原始描述，用于日志与兜底")

    @field_validator("interference")
    @classmethod
    def _dedupe(cls, value: list[Interference]) -> list[Interference]:
        seen: dict[Interference, None] = {}
        for item in value:
            seen.setdefault(item, None)
        return list(seen)

    def missing_critical(self) -> list[str]:
        """返回缺失的关键字段中文名，顺序固定，便于稳定输出。"""
        labels = {"target": "探测目标", "medium": "主要介质", "depth": "目标埋深"}
        missing: list[str] = []
        for name in CRITICAL_FIELDS:
            if getattr(self, name) is None:
                missing.append(labels[name])
        return missing

    def is_complete(self) -> bool:
        return not self.missing_critical()

    def merge(self, update: SiteConditions) -> SiteConditions:
        """用新抽取的条件覆盖旧条件，未提及的字段保持原值（多轮追问的核心）。"""
        merged = self.model_copy(deep=True)
        for name in type(self).model_fields:
            new_value = getattr(update, name)
            if name == "interference":
                if new_value:
                    merged.interference = list(new_value)
                continue
            if new_value is not None and new_value != "":
                setattr(merged, name, new_value)
        return merged

    def summary(self) -> str:
        """一行摘要，用于提示词与日志。"""
        parts = [
            f"目标={self.target.cn if self.target else '未知'}",
            f"介质={self.medium.cn if self.medium else '未知'}",
            f"埋深={self.depth if self.depth else '未知'}",
            f"地表={self.surface.value if self.surface else '未说明'}",
            "干扰="
            + ("、".join(item.cn for item in self.interference) if self.interference else "未说明"),
        ]
        return "，".join(parts)
