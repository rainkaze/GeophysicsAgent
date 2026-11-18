"""API 与 Agent 之间的稳定契约（DTO）。

原则：
- 请求/响应只包含可序列化的原始类型与领域模型；
- 响应结构足以支撑前端做结构化渲染，不需要再解析 Markdown；
- 正文 ``answer`` 与结构化 ``plan`` 由同一份数据生成，二者不会互相矛盾。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from geophysics_agent.domain.analysis import FieldDesign, MethodAssessment
from geophysics_agent.domain.conditions import SiteConditions
from geophysics_agent.domain.plan import SurveyPlan

Mode = Literal["agent", "clarification", "degraded"]


class RecommendRequest(BaseModel):
    """一次勘察方案推荐请求。"""

    message: str = Field(
        min_length=2,
        max_length=6000,
        description="自然语言场景描述（最短 2 字即可，信息不全时走追问而不是报错）",
    )
    conversation_id: str | None = Field(default=None, description="会话 id，缺省则新建")
    reset: bool = Field(default=False, description="为 true 时清空该会话历史后再处理")


class Evidence(BaseModel):
    """一条课程知识证据。"""

    id: str
    title: str
    content: str
    source: str
    page: int | None = None
    verification_status: str
    score: float = Field(description="BM25 相关性得分")
    matched_terms: list[str] = Field(
        default_factory=list, description="命中的检索词，用于解释相关性"
    )
    source_url: str | None = None
    citation: str | None = None


class TraceStep(BaseModel):
    """Agent 执行轨迹的一步，用于前端时间线与问题复盘。"""

    step: str
    status: Literal["ok", "warn", "error", "skipped"]
    detail: str
    duration_ms: int = 0


class Usage(BaseModel):
    """本次调用的模型用量统计。"""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ConditionView(BaseModel):
    """面向展示的场地条件（已本地化为中文），避免前端重复维护字典。"""

    target: str | None = None
    medium: str | None = None
    depth: str | None = None
    surface: str | None = None
    interference: str | None = None
    budget: str | None = None
    site_length: str | None = None


def build_condition_view(conditions: SiteConditions) -> ConditionView:
    """把枚举型条件转成可直接展示的中文文本。"""
    return ConditionView(
        target=conditions.target.cn if conditions.target else None,
        medium=conditions.medium.cn if conditions.medium else None,
        depth=str(conditions.depth) if conditions.depth else None,
        surface=conditions.surface.value if conditions.surface else None,
        interference=(
            "、".join(item.cn for item in conditions.interference)
            if conditions.interference
            else None
        ),
        budget=conditions.budget.value if conditions.budget else None,
        site_length=f"{conditions.site_length_m:g} m" if conditions.site_length_m else None,
    )


class RecommendResponse(BaseModel):
    """推荐结果。"""

    mode: Mode
    conversation_id: str
    answer: str = Field(description="面向人的 Markdown 正文，由结构化方案渲染而来")
    needs_clarification: bool = False
    questions: list[str] = Field(default_factory=list, description="需要用户补充的问题")
    conditions: SiteConditions
    conditions_view: ConditionView = Field(default_factory=ConditionView)
    missing_information: list[str] = Field(default_factory=list)
    plan: SurveyPlan | None = None
    assessments: list[MethodAssessment] = Field(default_factory=list)
    design: FieldDesign | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    evidence_quality: Literal["strong", "weak", "empty"] = "empty"
    warnings: list[str] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    elapsed_ms: int = 0
    disclaimer: str = ""
