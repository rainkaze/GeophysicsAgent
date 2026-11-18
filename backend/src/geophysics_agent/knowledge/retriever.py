"""BM25 词法检索 + 可选语义检索（向量 Embedding + Rerank，对齐 Dify）。

默认走 BM25（确定性、离线）。当配置了 DashScope key 且启用语义检索时，
走"BM25 + 向量 RRF 融合 → Rerank 重排"；任一环节失败都会自动回退到 BM25。

BM25 部分与旧版保持一致：中文按二元组切分、英文按词切分，字段加权
标题×3 / 关键词×2 / 正文×1，IDF 降权高频词，输出命中词与相关性分级。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from geophysics_agent.domain.schemas import Evidence
from geophysics_agent.knowledge.corpus import KnowledgeDocument, load_documents, searchable_text
from geophysics_agent.knowledge.semantic import SemanticClient, SemanticError

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

#: 字段权重（标题最关键，关键词次之，正文用于补充上下文）
FIELD_WEIGHTS: tuple[float, float, float] = (3.0, 2.0, 1.0)

#: BM25 参数
K1 = 1.5
B = 0.75

#: BM25 相关性分级阈值
STRONG_SCORE = 6.0
WEAK_SCORE = 2.0

#: rerank 分数（0~1 量级）的相关性分级阈值
RERANK_STRONG = 0.35
RERANK_WEAK = 0.1

#: 混合检索参数：BM25/向量各自的候选池大小、RRF 常数、重排候选倍数
BM25_POOL = 50
RRF_K = 60
RERANK_CANDIDATES_MULT = 3

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
    """预处理后的单条知识片段。"""

    record: KnowledgeDocument
    term_freq: dict[str, float]
    length: float


@dataclass
class RetrievalResult:
    """一次检索的结果与质量标记。"""

    evidence: list[Evidence] = field(default_factory=list)
    quality: Quality = "empty"
    top_score: float = 0.0


class Retriever:
    """混合检索器：BM25 兜底 + 可选向量/重排。"""

    def __init__(
        self,
        top_k: int = 5,
        weak_score: float = WEAK_SCORE,
        semantic: SemanticClient | None = None,
    ) -> None:
        self.top_k = top_k
        self.weak_score = weak_score
        self.semantic = semantic
        self._documents: list[_Document] | None = None
        self._idf: dict[str, float] = {}
        self._avg_length = 1.0
        self._vectors: dict[str, list[float]] | None = None

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

    def _ensure_vectors(self) -> None:
        if self._vectors is not None:
            return
        if self.semantic is None or not self.semantic.available:
            self._vectors = {}
            return
        assert self._documents is not None
        records = [document.record for document in self._documents]
        self._vectors = self.semantic.embed_documents(records)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _bm25_score(self, query_terms: list[str], document: _Document) -> tuple[float, list[str]]:
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
        matched.sort(reverse=True)
        return score, [term for _, term in matched[:5]]

    @staticmethod
    def _to_evidence(score: float, document: _Document, matched_terms: list[str]) -> Evidence:
        record = document.record
        return Evidence(
            id=record.id,
            title=record.title,
            content=record.content,
            source=record.source,
            page=record.page,
            verification_status=record.status,
            score=round(score, 3),
            matched_terms=matched_terms,
            source_url=record.source_url,
            citation=record.citation,
        )

    def search(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """返回按相关性排序的证据列表及质量等级。"""
        self._ensure_index()
        assert self._documents is not None

        limit = top_k or self.top_k
        terms = tokenize(query)
        if not terms:
            return RetrievalResult()

        query_terms = list(dict.fromkeys(terms))
        scored: list[tuple[float, _Document, list[str]]] = []
        for document in self._documents:
            score, matched = self._bm25_score(query_terms, document)
            if score > 0:
                scored.append((score, document, matched))
        scored.sort(key=lambda item: item[0], reverse=True)

        # 向量检索必须**先于**"BM25 无命中就返回空"执行：
        # 中文提问 + 英文教材本来就没有词面交集，BM25 必然为 0，
        # 若在这里早退，embedding 恰好在最需要它的场景里永远不被调用。
        if self.semantic is not None and self.semantic.available:
            try:
                return self._semantic_search(query, scored, limit)
            except SemanticError:
                # 语义检索失败 → 自动回退 BM25，保证可离线出结果
                pass

        if not scored:
            return RetrievalResult()

        top_score = round(scored[0][0], 2)
        quality: Quality = (
            "strong"
            if top_score >= STRONG_SCORE
            else "weak"
            if top_score >= self.weak_score
            else "empty"
        )
        evidence = [
            self._to_evidence(score, doc, matched) for score, doc, matched in scored[:limit]
        ]
        return RetrievalResult(evidence=evidence, quality=quality, top_score=top_score)

    def _semantic_search(
        self,
        query: str,
        scored: list[tuple[float, _Document, list[str]]],
        limit: int,
    ) -> RetrievalResult:
        """BM25 + 向量 RRF 融合 → Rerank 重排。"""
        self._ensure_vectors()
        assert self._documents is not None
        assert self.semantic is not None

        if not self._vectors:
            raise SemanticError("语义检索不可用：无向量")

        query_vector = self.semantic.embed([query])[0]
        vec_scored: list[tuple[float, _Document]] = []
        for document in self._documents:
            vector = self._vectors.get(document.record.id)
            if vector is None:
                continue
            similarity = self._cosine(query_vector, vector)
            if similarity > 0:
                vec_scored.append((similarity, document))
        vec_scored.sort(key=lambda item: item[0], reverse=True)

        bm25_pool = [(score, doc) for score, doc, _ in scored[:BM25_POOL]]
        fused = self._rrf([bm25_pool, vec_scored[:BM25_POOL]])
        candidate_count = max(limit * RERANK_CANDIDATES_MULT, limit + 3)
        candidates = [document for document, _ in fused[:candidate_count]]
        if not candidates:
            raise SemanticError("语义检索无可召回候选")

        rerank_scores = self.semantic.rerank(
            query, [document.record.content for document in candidates], len(candidates)
        )
        ranked = sorted(zip(candidates, rerank_scores, strict=True), key=lambda item: -item[1])
        top = ranked[:limit]

        matched_by_id = {document.record.id: matched for _, document, matched in scored}
        evidence = [
            self._to_evidence(score, document, matched_by_id.get(document.record.id, []))
            for document, score in top
        ]
        top_score = round(top[0][1], 3)
        quality: Quality = (
            "strong"
            if top_score >= RERANK_STRONG
            else "weak"
            if top_score >= RERANK_WEAK
            else "empty"
        )
        return RetrievalResult(evidence=evidence, quality=quality, top_score=top_score)

    @staticmethod
    def _rrf(ranked_lists: list[list[tuple[float, _Document]]]) -> list[tuple[_Document, float]]:
        """Reciprocal Rank Fusion：把多个排序列表融合成单一排序。"""
        merged: dict[str, tuple[float, _Document]] = {}
        for ranked in ranked_lists:
            for rank, (_, document) in enumerate(ranked):
                key = document.record.id
                current, _ = merged.get(key, (0.0, document))
                merged[key] = (current + 1.0 / (RRF_K + rank + 1), document)
        ordered = sorted(merged.values(), key=lambda item: -item[0])
        return [(document, score) for score, document in ordered]
