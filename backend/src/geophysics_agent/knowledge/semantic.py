"""DashScope 语义检索：向量 Embedding + Rerank（对齐 Dify 的混合检索）。

只在配置了 ``DASHSCOPE_API_KEY`` 且 ``ENABLE_SEMANTIC_RETRIEVAL=true`` 时才启用；
未配置时 ``build_semantic_client`` 返回 ``None``，检索层回退到本地 BM25（离线兜底）。

- Embedding：走 OpenAI 兼容接口 ``/embeddings``，模型 ``text-embedding-v4``；
- Rerank：走 DashScope 原生接口，模型 ``qwen3-rerank``。
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

import httpx
from openai import OpenAI

from geophysics_agent.core.config import BACKEND_ROOT, Settings

RERANK_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
CACHE_PATH = BACKEND_ROOT / "data" / "knowledge" / ".embedding_cache.json"
EMBED_BATCH = 10


class SemanticError(RuntimeError):
    """embedding / rerank 调用失败。"""


class SemanticClient:
    """阿里云百炼（DashScope）的 embedding 与 rerank 客户端。"""

    def __init__(self, settings: Settings) -> None:
        self._key = settings.dashscope_api_key
        self._embedding_model = settings.embedding_model
        self._rerank_model = settings.rerank_model
        self._client = OpenAI(
            api_key=self._key,
            base_url=settings.dashscope_base_url,
            timeout=60.0,
            max_retries=1,
        )
        self._lock = threading.Lock()
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    @property
    def available(self) -> bool:
        return bool(self._key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量取得向量；失败抛 ``SemanticError``。"""
        vectors: list[list[float]] = []
        try:
            for start in range(0, len(texts), EMBED_BATCH):
                batch = texts[start : start + EMBED_BATCH]
                response = self._client.embeddings.create(model=self._embedding_model, input=batch)
                vectors.extend(item.embedding for item in response.data)
        except Exception as exc:
            raise SemanticError(f"embedding 调用失败：{type(exc).__name__}") from exc
        return vectors

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[float]:
        """返回与 documents 同序的相关性得分；未进入 top_n 的为 0.0。"""
        if not documents:
            return []
        try:
            response = httpx.post(
                RERANK_URL,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._rerank_model,
                    "input": {"query": query, "documents": documents},
                    "parameters": {"return_documents": False, "top_n": top_n},
                },
                timeout=60.0,
            )
            if response.status_code != 200:
                raise SemanticError(
                    f"rerank 调用失败（HTTP {response.status_code}）：{response.text[:200]}"
                )
            scores = [0.0] * len(documents)
            for item in response.json()["output"]["results"]:
                scores[item["index"]] = item["relevance_score"]
        except SemanticError:
            raise
        except Exception as exc:
            raise SemanticError(f"rerank 调用失败：{type(exc).__name__}") from exc
        return scores

    def embed_documents(self, records: list[Any]) -> dict[str, list[float]]:
        """批量取得文档向量，带本地缓存（内容变更自动重算）。"""
        result: dict[str, list[float]] = {}
        missing: list[Any] = []
        with self._lock:
            for record in records:
                digest = hashlib.md5(record.content.encode("utf-8")).hexdigest()[:10]
                cached = self._cache.get(record.id)
                if cached and cached.get("hash") == digest:
                    result[record.id] = cached["vec"]
                else:
                    missing.append(record)
            if missing:
                vectors = self.embed([record.content for record in missing])
                for record, vector in zip(missing, vectors, strict=True):
                    digest = hashlib.md5(record.content.encode("utf-8")).hexdigest()[:10]
                    self._cache[record.id] = {"hash": digest, "vec": vector}
                    result[record.id] = vector
                self._save_cache()
        return result

    def _load_cache(self) -> None:
        try:
            if CACHE_PATH.exists():
                self._cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._cache = {}

    def _save_cache(self) -> None:
        try:
            CACHE_PATH.write_text(json.dumps(self._cache, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def build_semantic_client(settings: Settings) -> SemanticClient | None:
    """按配置构造语义检索客户端；未启用或无 key 时返回 None。"""
    if not settings.enable_semantic_retrieval or not settings.dashscope_api_key:
        return None
    return SemanticClient(settings)
