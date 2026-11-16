"""BM25 课程知识检索。

相比朴素字面交集，本实现做了四件事：
1. **IDF 加权**：语料中到处出现的泛化二元组（"工程""物探"）权重自动降低；
2. **字段加权**（BM25F 近似）：标题 ×3、关键词 ×2、正文 ×1；
3. **长度归一**：长条目不会因为词多而占优；
4. **相关性分级**：给出 ``strong / weak / empty`` 与命中词，前端可据此提示
   "本次证据较弱"，而不是假装 5 条都相关。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal

from geophysics_agent.domain.schemas import Evidence
from geophysics_agent.knowledge.corpus import load_documents, searchable_text

#: 中文检索的停用二元组（只收功能词，领域词交给 IDF 处理）
_CJK_STOPWORDS: frozenset[str] = frozenset(
    {
        "我们",
        "你们",
        "他们",
        "可以",
        "需要",
        "进行",
        "以及",
        "或者",
        "这个",
        "那个",
        "一个",
        "什么",
        "如何",
        "是否",
        "没有",
        "通过",
        "对于",
        "由于",
        "如果",
        "但是",
        "而且",
        "并且",
        "然后",
        "其中",
        "这些",
        "那些",
        "这样",
        "那样",
        "不是",
        "就是",
        "还是",
        "可能",
        "应该",
        "必须",
        "能够",
        "因此",
        "所以",
        "以上",
        "以下",
        "方面",
        "相关",
        "具有",
        "包括",
        "属于",
        "用来",
        "用于",
        "提供",
        "请给",
        "给出",
        "一下",
    }
)
_LATIN_STOPWORDS: frozenset[str] = frozenset(
    {"the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "has", "have"}
)

_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
_LATIN_WORD = re.compile(r"[a-z0-9]+")

#: 字段权重（标题最关键，正文用于补充上下文）
FIELD_WEIGHTS: tuple[float, float, float] = (3.0, 2.0, 1.0)

#: BM25 参数
K1 = 1.5
B = 0.75

#: 相关性分级阈值（BM25 得分量级）
STRONG_SCORE = 6.0
WEAK_SCORE = 2.0

Quality = Literal["strong", "weak", "empty"]


def tokenize(text: str) -> list[str]:
    """中文按二元组切分，英文/数字按词切分，并过滤停用词。"""
    if not text:
        return []
    tokens: list[str] = []
    for word in _LATIN_WORD.findall(text.lower()):
        if word not in _LATIN_STOPWORDS:
            tokens.append(word)
    for run in _CJK_RUN.findall(text):
        if len(run) == 1:
            tokens.append(run)
            continue
        for index in range(len(run) - 1):
            bigram = run[index : index + 2]
            if bigram not in _CJK_STOPWORDS:
                tokens.append(bigram)
    return tokens


@dataclass
class _Document:
    """预处理后的单条知识。"""

    record: dict[str, Any]
    term_freq: dict[str, float]
    length: float


@dataclass
class RetrievalResult:
    """一次检索的结果与质量标记。"""

    evidence: list[Evidence] = field(default_factory=list)
    quality: Quality = "empty"
    top_score: float = 0.0


class Retriever:
    """BM25 检索器；索引在首次使用时构建并缓存。"""

    def __init__(self, top_k: int = 5, weak_score: float = WEAK_SCORE) -> None:
        self.top_k = top_k
        self.weak_score = weak_score
        self._documents: list[_Document] | None = None
        self._idf: dict[str, float] = {}
        self._avg_length = 1.0

    def _ensure_index(self) -> None:
        if self._documents is not None:
            return
        records = load_documents()
        documents: list[_Document] = []
        for record in records:
            title, keywords, content = searchable_text(record)
            weighted: dict[str, float] = {}
            for text, weight in zip((title, keywords, content), FIELD_WEIGHTS, strict=True):
                for token, count in Counter(tokenize(text)).items():
                    weighted[token] = weighted.get(token, 0.0) + count * weight
            documents.append(
                _Document(
                    record=record,
                    term_freq=weighted,
                    length=float(sum(weighted.values())) or 1.0,
                )
            )

        total = len(documents)
        df: Counter[str] = Counter()
        for document in documents:
            for term in document.term_freq:
                df[term] += 1
        self._idf = {
            term: math.log(1.0 + (total - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()
        }
        self._avg_length = sum(document.length for document in documents) / total
        self._documents = documents

    def search(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """返回按 BM25 排序的证据列表及质量等级。"""
        self._ensure_index()
        assert self._documents is not None

        terms = tokenize(query)
        if not terms:
            return RetrievalResult()

        query_terms = list(dict.fromkeys(terms))
        scored: list[tuple[float, _Document, list[str]]] = []
        for document in self._documents:
            score = 0.0
            matched: list[tuple[float, str]] = []
            for term in query_terms:
                frequency = document.term_freq.get(term)
                if not frequency:
                    continue
                idf = self._idf.get(term, 0.0)
                denominator = frequency + K1 * (1 - B + B * document.length / self._avg_length)
                score += idf * frequency * (K1 + 1) / denominator
                matched.append((idf, term))
            if score <= 0:
                continue
            matched.sort(reverse=True)
            scored.append((score, document, [term for _, term in matched[:5]]))

        if not scored:
            return RetrievalResult()

        scored.sort(key=lambda item: item[0], reverse=True)
        limit = top_k or self.top_k
        top_score = round(scored[0][0], 2)
        quality: Quality = (
            "strong"
            if top_score >= STRONG_SCORE
            else "weak"
            if top_score >= self.weak_score
            else "empty"
        )

        evidence: list[Evidence] = []
        for score, document, matched_terms in scored[:limit]:
            record = document.record
            evidence.append(
                Evidence(
                    id=str(record["id"]),
                    title=str(record["title"]),
                    content=str(record["content"]),
                    source=str(record["source"]),
                    page=record.get("page"),
                    verification_status=str(record["verification_status"]),
                    score=round(score, 2),
                    matched_terms=matched_terms,
                    source_url=record.get("source_url"),
                    citation=record.get("citation"),
                )
            )
        return RetrievalResult(evidence=evidence, quality=quality, top_score=top_score)


_default_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    """进程级共享检索器（索引只构建一次）。"""
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = Retriever()
    return _default_retriever


def retrieve(query: str, top_k: int = 5) -> list[Evidence]:
    """便捷函数，兼容旧调用方式。"""
    return get_retriever().search(query, top_k).evidence
