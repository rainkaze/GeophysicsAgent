"""集中管理运行配置（只从环境变量或本机 .env 读取）。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    """应用配置；密钥只从环境或本机 .env 读取，绝不进入浏览器。"""

    # --- 模型 ---
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    enable_llm: bool = True

    # --- 应用 ---
    app_log_level: str = "INFO"

    # --- 检索 ---
    knowledge_top_k: int = Field(default=5, ge=1, le=10)

    # --- 语义检索（对齐 Dify：向量 Embedding + Rerank）---
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v4"
    rerank_model: str = "qwen3-rerank"
    enable_semantic_retrieval: bool = True

    # --- 规划与校验 ---
    planner_max_repairs: int = Field(default=1, ge=0, le=3)

    # --- 会话 ---
    session_max_sessions: int = Field(default=200, ge=1)
    session_ttl_minutes: int = Field(default=120, ge=1)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """进程级单例配置。"""
    return Settings()
