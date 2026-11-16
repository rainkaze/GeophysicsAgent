"""HTTP 路由：只做协议转换、鉴权边界与错误映射，不含业务逻辑。"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from geophysics_agent.agent.runner import AgentRunner, build_runner
from geophysics_agent.domain.scenarios import SCENARIOS, Scenario
from geophysics_agent.domain.schemas import RecommendRequest, RecommendResponse
from geophysics_agent.knowledge.corpus import KnowledgeBaseError

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)


def get_runner() -> AgentRunner:
    """依赖注入入口：测试可用 ``app.dependency_overrides`` 替换。"""
    return build_runner()


@router.get("/health", summary="健康检查")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/scenarios", response_model=list[Scenario], summary="内置演示场景")
def list_scenarios() -> list[Scenario]:
    """返回课程演示用的标准场景，供前端一键填入。"""
    return list(SCENARIOS)


@router.post("/recommend", response_model=RecommendResponse, summary="生成勘察方案")
def recommend(
    request: RecommendRequest,
    runner: Annotated[AgentRunner, Depends(get_runner)],
) -> RecommendResponse:
    """接收自然语言场景，返回结构化方案与执行轨迹。"""
    try:
        return runner.run(
            request.message,
            request.conversation_id,
            reset=request.reset,
        )
    except KnowledgeBaseError as exc:
        logger.error("知识库不可用：%s", exc)
        raise HTTPException(status_code=503, detail="课程知识库不可用，请检查部署文件") from exc
    except RuntimeError as exc:
        logger.error("运行配置错误：%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Agent 请求执行失败")
        raise HTTPException(
            status_code=502,
            detail="方案生成失败，请检查模型服务配置或稍后重试",
        ) from exc
