"""HTTP API 路由。"""

import logging

from fastapi import APIRouter, HTTPException

from geophysics_agent.agent.runner import run_agent
from geophysics_agent.domain.schemas import RecommendRequest, RecommendResponse

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    try:
        return run_agent(request.message, request.conversation_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # 不向客户端暴露供应商响应、请求细节或可能的敏感信息。
        logger.exception("Agent 请求执行失败")
        raise HTTPException(
            status_code=502,
            detail="模型服务调用失败，请检查服务配置或稍后重试。",
        ) from exc
