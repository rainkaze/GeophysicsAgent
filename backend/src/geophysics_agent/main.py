"""FastAPI 应用入口：中间件、CORS 与请求观测。"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from geophysics_agent.api.routes import router
from geophysics_agent.core.config import get_settings

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

logger = logging.getLogger("geophysics_agent.http")


def create_app() -> FastAPI:
    """构造应用实例（便于测试中重复创建）。"""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = FastAPI(
        title="工程物探勘察方案推荐 Agent",
        version="0.2.0",
        description="面向工程物探课程的自然语言场景 → 结构化勘察方案推荐服务",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)

    @app.middleware("http")
    async def request_observability(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    return app


app = create_app()
