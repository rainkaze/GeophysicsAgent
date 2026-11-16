"""API 与 Agent 的稳定输入输出模型。"""

from typing import Any

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    message: str = Field(min_length=8, max_length=6000)
    conversation_id: str | None = None


class Evidence(BaseModel):
    id: str
    title: str
    content: str
    source: str
    page: int | None = None
    verification_status: str
    score: float
    source_url: str | None = None
    citation: str | None = None


class AgentEvent(BaseModel):
    event: str
    status: str
    detail: str


class RecommendResponse(BaseModel):
    mode: str
    conversation_id: str
    answer: str
    extracted_conditions: dict[str, Any]
    missing_information: list[str]
    evidence: list[Evidence]
    tool_result: dict[str, Any] | None
    events: list[AgentEvent]
    disclaimer: str
