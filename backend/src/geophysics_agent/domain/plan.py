"""方案模型：大模型产出的草案、校验结论、以及最终可交付方案。

数据流：
``PlanDraft``（模型输出，只含角色与理由）
    → ``Verifier``（确定性校验，产出 ``Violation``）
    → ``SurveyPlan``（校验后的方案 + 追溯信息 + 渲染正文）
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from geophysics_agent.domain.enums import Method, Role


class Risk(BaseModel):
    """一条工程风险及其对策。"""

    risk: str = Field(min_length=2, max_length=80)
    impact: str = Field(min_length=2, max_length=120)
    response: str = Field(min_length=2, max_length=160)


class PlanItem(BaseModel):
    """方案中的一个方法条目。数值由外部评估补充，模型只给角色与理由。"""

    method: Method
    role: Role
    rationale: str = Field(min_length=4, max_length=400)
    mitigation: str | None = Field(default=None, max_length=240)

    @field_validator("method", mode="before")
    @classmethod
    def _normalize_method(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("role", mode="before")
    @classmethod
    def _normalize_role(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            aliases = {
                "主方法": Role.PRIMARY,
                "primary": Role.PRIMARY,
                "主要方法": Role.PRIMARY,
                "辅助": Role.SUPPORT,
                "辅助方法": Role.SUPPORT,
                "support": Role.SUPPORT,
                "验证": Role.VERIFICATION,
                "验证方法": Role.VERIFICATION,
                "verification": Role.VERIFICATION,
                "不建议": Role.EXCLUDED,
                "不建议采用": Role.EXCLUDED,
                "excluded": Role.EXCLUDED,
            }
            return aliases.get(text, value)
        return value


class PlanDraft(BaseModel):
    """大模型输出的方案草案（严格 schema，多余字段直接拒绝）。"""

    summary: str = Field(min_length=8, max_length=400)
    items: list[PlanItem] = Field(min_length=1, max_length=8)
    risks: list[Risk] = Field(min_length=1, max_length=8)
    verification: list[str] = Field(min_length=1, max_length=8)
    missing_information: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def _single_primary(self) -> PlanDraft:
        primaries = [item for item in self.items if item.role is Role.PRIMARY]
        if len(primaries) > 1:
            raise ValueError("只能选择一个主方法")
        seen: set[Method] = set()
        for item in self.items:
            if item.method in seen:
                raise ValueError(f"方法 {item.method.value} 重复出现")
            seen.add(item.method)
        return self

    def primary(self) -> PlanItem | None:
        for item in self.items:
            if item.role is Role.PRIMARY:
                return item
        return None


class Violation(BaseModel):
    """校验器发现的一条问题。error 会触发修复循环，warning 只提示。"""

    code: str
    severity: Literal["error", "warning"]
    message: str


class SurveyPlan(BaseModel):
    """校验后的最终方案。"""

    summary: str
    items: list[PlanItem]
    risks: list[Risk]
    verification: list[str]
    missing_information: list[str] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)
    degraded: bool = Field(default=False, description="模型不可用或修复失败时回退到规则方案")
    narrative: str = Field(default="", description="由渲染器生成的 Markdown 正文")

    def primary_method(self) -> Method | None:
        for item in self.items:
            if item.role is Role.PRIMARY:
                return item.method
        return None
