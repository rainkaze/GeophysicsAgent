"""课程知识语料：加载、缓存与字段抽取。

语料是 ``backend/data/knowledge/course_knowledge.json``，每条记录包含
``id / title / content / source / page / verification_status / keywords / citation``。
本模块只负责"把数据读进来并保持最新"，不做任何检索逻辑。
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from geophysics_agent.core.config import BACKEND_ROOT

DATA_PATH = BACKEND_ROOT / "data" / "knowledge" / "course_knowledge.json"

_lock = threading.Lock()
_cache: list[dict[str, Any]] | None = None
_cached_mtime: float | None = None


class KnowledgeBaseError(RuntimeError):
    """语料文件缺失或格式非法。"""


def load_documents() -> list[dict[str, Any]]:
    """返回全部知识条目；文件变更时自动重新加载。"""
    global _cache, _cached_mtime

    if not DATA_PATH.exists():
        raise KnowledgeBaseError(f"知识库文件不存在：{DATA_PATH}")

    mtime = DATA_PATH.stat().st_mtime
    with _lock:
        if _cache is not None and _cached_mtime == mtime:
            return _cache

        try:
            raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - 数据损坏时的兜底
            raise KnowledgeBaseError(f"知识库 JSON 解析失败：{exc}") from exc

        if not isinstance(raw, list) or not raw:
            raise KnowledgeBaseError("知识库内容为空或格式不是数组")

        required = {"id", "title", "content", "source", "verification_status"}
        for index, item in enumerate(raw):
            missing = required - set(item)
            if missing:
                raise KnowledgeBaseError(f"第 {index} 条知识缺少字段：{sorted(missing)}")

        _cache = raw
        _cached_mtime = mtime
        return _cache


def invalidate_cache() -> None:
    """测试或热更新时强制下次重新加载。"""
    global _cache, _cached_mtime
    with _lock:
        _cache = None
        _cached_mtime = None


def searchable_text(document: dict[str, Any]) -> tuple[str, str, str]:
    """返回（标题、关键词、正文）三段文本，供检索器加权。"""
    title = str(document.get("title", ""))
    keywords = " ".join(str(word) for word in document.get("keywords", []))
    content = str(document.get("content", ""))
    return title, keywords, content


def data_path() -> Path:
    """暴露路径，便于诊断命令与测试引用。"""
    return DATA_PATH
