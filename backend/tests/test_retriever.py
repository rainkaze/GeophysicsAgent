"""检索器测试：验证 IDF 排序、相关性分级与命中词解释。"""

from __future__ import annotations

import pytest

from geophysics_agent.knowledge.retriever import Retriever, tokenize
from geophysics_agent.knowledge.semantic import SemanticError


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever(top_k=5)


def test_tokenize_handles_chinese_bigrams_and_latin() -> None:
    tokens = tokenize("探地雷达 GPR 与溶洞")

    assert "探地" in tokens
    assert "gpr" in tokens
    assert "溶洞" in tokens


def test_tokenize_drops_function_words() -> None:
    assert "可以" not in tokenize("可以给出方案")


def test_relevant_query_returns_target_specific_evidence(retriever: Retriever) -> None:
    result = retriever.search("灰岩溶洞空洞探测")

    assert result.evidence
    assert result.quality in {"strong", "weak"}
    joined = " ".join(item.title + item.content for item in result.evidence)
    assert "溶洞" in joined or "空洞" in joined or "电阻率" in joined


def test_evidence_carries_explanation_terms(retriever: Retriever) -> None:
    result = retriever.search("电阻率反演非唯一性")

    assert result.evidence
    top = result.evidence[0]
    assert top.matched_terms
    assert top.score > 0
    assert top.source


def test_unrelated_query_returns_nothing(retriever: Retriever) -> None:
    result = retriever.search("今天北京天气怎么样")

    assert result.evidence == []
    assert result.quality == "empty"


def test_scores_are_sorted_descending(retriever: Retriever) -> None:
    result = retriever.search("探地雷达 GPR 电阻率 面波")

    scores = [item.score for item in result.evidence]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------- 语义检索
class _FakeSemantic:
    """离线假语义客户端：用确定性向量与简单字符串匹配模拟 embedding/rerank。"""

    available = True

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(sum(map(ord, text)) % 97) / 97.0, 1.0] for text in texts]

    def embed_documents(self, records: list) -> dict[str, list[float]]:
        return {record.id: [float(len(record.content) % 97) / 97.0, 1.0] for record in records}

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[float]:
        key = query[:2]
        return [0.9 if key in document else 0.1 for document in documents]


class _BrokenSemantic:
    available = True

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise SemanticError("boom")

    def embed_documents(self, records: list) -> dict[str, list[float]]:
        raise SemanticError("boom")

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[float]:
        raise SemanticError("boom")


def test_semantic_retrieval_uses_rerank_scores() -> None:
    retriever = Retriever(top_k=5, semantic=_FakeSemantic())
    result = retriever.search("电阻率反演")

    assert result.evidence
    assert all(0.0 <= item.score <= 1.0 for item in result.evidence)


def test_semantic_failure_falls_back_to_bm25() -> None:
    retriever = Retriever(top_k=5, semantic=_BrokenSemantic())
    result = retriever.search("电阻率反演非唯一性")

    assert result.evidence
    assert any(item.score > 0 for item in result.evidence)


def test_semantic_runs_even_when_bm25_has_no_hit() -> None:
    """中文提问 + 英文语料时 BM25 为 0，向量检索仍必须执行。"""
    retriever = Retriever(top_k=3, semantic=_FakeSemantic())
    result = retriever.search("今天北京天气怎么样")

    assert result.evidence, "BM25 无命中时不应直接返回空，向量召回还没跑"
    assert all(0.0 <= item.score <= 1.0 for item in result.evidence)


def test_empty_bm25_and_broken_semantic_returns_nothing() -> None:
    retriever = Retriever(top_k=3, semantic=_BrokenSemantic())
    result = retriever.search("今天北京天气怎么样")

    assert result.evidence == []
    assert result.quality == "empty"
