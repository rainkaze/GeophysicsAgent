"""可解释的本地课程知识检索。"""

import json
import re

from geophysics_agent.core.config import BACKEND_ROOT
from geophysics_agent.domain.schemas import Evidence

DATA_PATH = BACKEND_ROOT / "data" / "knowledge" / "course_knowledge.json"


def retrieve(query: str, top_k: int = 5) -> list[Evidence]:
    if not DATA_PATH.exists():
        return []
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    terms.update(_cjk_bigrams(query))
    hits: list[Evidence] = []
    for row in records:
        text = " ".join([row["title"], row["content"], *row.get("keywords", [])]).lower()
        words = set(re.findall(r"[a-z0-9]+", text))
        words.update(_cjk_bigrams(text))
        score = len(terms & words) / max(1, len(terms))
        if score:
            hits.append(Evidence(**{**row, "score": round(score, 3)}))
    return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]


def _cjk_bigrams(text: str) -> set[str]:
    """以相邻汉字二元组处理中文无空格分词的检索问题。"""
    cjk_runs = re.findall(r"[\u4e00-\u9fff]+", text)
    return {run[index : index + 2] for run in cjk_runs for index in range(len(run) - 1)}
