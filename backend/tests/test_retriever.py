"""检索器测试：验证 IDF 排序、相关性分级与命中词解释。"""

from __future__ import annotations

import pytest

from geophysics_agent.knowledge.retriever import Retriever, tokenize


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
