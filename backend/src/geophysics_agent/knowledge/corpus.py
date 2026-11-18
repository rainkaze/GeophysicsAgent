"""知识库加载：扫描目录里的 Markdown 文件，切分为可检索的片段。

设计目标——"加一个文件就生效"：

- 知识库就是 ``backend/data/knowledge/`` 下的若干个 ``.md`` 文件（可放子目录）；
- 启动后自动扫描全部 ``.md``，无需登记任何清单；
- 新增一个 ``.md`` 文件，下次请求即被索引（按文件 mtime 缓存，改动自动重载）。

文件约定（均为可选，不写也能用）：

1. 文件顶部可用 YAML 风格 front-matter 声明文件级元数据：:

       ---
       source: 来源名称
       status: 核对状态
       keywords: 关键词1、关键词2
       ---

2. 正文里的印刷页码标记 ``[p.N]`` 会被识别为页码（教材用），并成为片段引用的页码。

3. 每个 ``##``/``###`` 小节是一个检索单元；小节下方可用 HTML 注释记录
   该条目的元数据：:

       <!-- meta: source=... | page=13 | status=... | keywords=... | citation=... -->

片段字段：``id / title / content / source / page / status / keywords / citation``。
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

from geophysics_agent.core.config import BACKEND_ROOT

KNOWLEDGE_DIR = BACKEND_ROOT / "data" / "knowledge"

#: 教材来源的规范名（book/ 子目录里的文件默认来源）
BOOK_SOURCE = "An Introduction to Geophysical Exploration (3rd ed., Kearey, Brooks & Hill, 2002)"
#: 教材分章的核对状态（直接来自 PDF 原文并带页码标记，可作为原文引用）
BOOK_STATUS = "教材原文（分章全文，带页码标记）"

#: 片段目标长度（字符），硬上限用于强行切分超长段
CHUNK_TARGET = 600
CHUNK_HARD_CAP = 1100

_PAGE_MARKER = re.compile(r"^\[p\.(\d+)\]$")
_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_META_COMMENT = re.compile(r"^<!--\s*meta:\s*(.*?)\s*-->$")
#: 小节标题形如 "ID｜标题"，用于保留有意义的知识条目编号
_HEADING_WITH_ID = re.compile(r"^(?P<id>[A-Za-z0-9][A-Za-z0-9_-]*)｜(?P<title>.+)$")


class KnowledgeBaseError(RuntimeError):
    """知识库目录为空或某个文件格式非法。"""


@dataclass(frozen=True)
class KnowledgeDocument:
    """知识库中的一个可检索片段。"""

    id: str
    title: str
    content: str
    source: str
    page: int | None
    status: str
    keywords: list[str] = field(default_factory=list)
    citation: str | None = None
    source_url: str | None = None


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """解析文件顶部的 ``---`` 分隔 front-matter；没有则返回空字典与原文。"""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}, text
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, "\n".join(lines[end + 1 :])


def _parse_meta_comment(raw: str) -> dict[str, str]:
    """解析 ``key=value | key=value`` 形式的 meta 注释。"""
    meta: dict[str, str] = {}
    for part in raw.split("|"):
        if "=" in part:
            key, _, value = part.partition("=")
            meta[key.strip()] = value.strip()
    return meta


def _split_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[、，,;；]+", value) if item.strip()]


def _chunk_texts(texts: list[str], target: int, hard_cap: int) -> list[str]:
    """把若干段落聚合成接近 target 长度的片段，保持段落完整、超长段硬切。"""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0

    for raw in texts:
        text = raw.strip()
        if not text:
            continue
        if len(text) > hard_cap:
            flush()
            # 超长段按句硬切
            start = 0
            while start < len(text):
                end = min(start + target, len(text))
                if end < len(text):
                    cut = text.rfind(" ", start, end)
                    if cut > start:
                        end = cut
                chunks.append(text[start:end].strip())
                start = end
            continue
        if current and current_len + len(text) + 1 > target:
            flush()
        current.append(text)
        current_len += len(text) + 1
    flush()
    return chunks


def _derive_source(rel_dir: str, filename: str, meta: dict[str, str]) -> str:
    if meta.get("source"):
        return meta["source"]
    if rel_dir.split("/")[0] == "book":
        return BOOK_SOURCE
    return filename


def _parse_file(path: Path) -> list[KnowledgeDocument]:
    """解析单个知识文件为若干片段。"""
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    file_keywords = _split_keywords(meta.get("keywords"))
    rel_dir = str(path.parent.relative_to(KNOWLEDGE_DIR)).replace("\\", "/")
    if rel_dir == ".":
        rel_dir = ""
    source = _derive_source(rel_dir, path.stem, meta)
    is_book = rel_dir.split("/")[0] == "book"
    file_status = meta.get("status", BOOK_STATUS if is_book else "未标注核对状态")

    current_page: int | None = None
    current_title = path.stem
    current_id: str | None = None
    current_status = file_status
    current_keywords = file_keywords
    current_citation: str | None = None
    current_source_url: str | None = None
    buffer: list[str] = []
    documents: list[KnowledgeDocument] = []
    file_seq = 0

    def flush() -> None:
        nonlocal buffer, current_title, file_seq
        if not any(part.strip() for part in buffer):
            buffer = []
            return
        pieces = _chunk_texts(buffer, CHUNK_TARGET, CHUNK_HARD_CAP)
        for index, piece in enumerate(pieces, start=1):
            file_seq += 1
            if current_id:
                chunk_id = current_id if len(pieces) == 1 else f"{current_id}.{index}"
            else:
                chunk_id = f"{path.stem}#{file_seq}"
            citation = current_citation or (
                f"{source}, p.{current_page}" if current_page is not None else source
            )
            documents.append(
                KnowledgeDocument(
                    id=chunk_id,
                    title=current_title,
                    content=piece,
                    source=source,
                    page=current_page,
                    status=current_status,
                    keywords=list(current_keywords),
                    citation=citation,
                    source_url=current_source_url,
                )
            )
        buffer = []

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue

        marker = _PAGE_MARKER.match(stripped)
        if marker:
            flush()
            current_page = int(marker.group(1))
            current_id = None
            current_status = file_status
            current_keywords = file_keywords
            current_citation = None
            current_source_url = None
            continue

        heading = _HEADING.match(stripped)
        if heading:
            flush()
            text_heading = heading.group(2).strip()
            current_id = None
            current_status = file_status
            current_keywords = file_keywords
            current_citation = None
            current_source_url = None
            with_id = _HEADING_WITH_ID.match(text_heading)
            if with_id:
                current_id = with_id.group("id")
                current_title = with_id.group("title").strip()
            else:
                # 去掉教材标题里的章号前缀 "1 The ..." → "The ..."
                current_title = re.sub(r"^\d+\s+", "", text_heading).strip()
            continue

        meta_comment = _META_COMMENT.match(stripped)
        if meta_comment:
            section_meta = _parse_meta_comment(meta_comment.group(1))
            # 小节级 meta 是完整覆盖：先回到文件默认，再按 key 覆盖，
            # 避免未写 page 的条目沿用上一条的 page。
            current_page = None
            current_status = file_status
            current_keywords = file_keywords
            current_citation = None
            current_source_url = None
            if section_meta.get("page"):
                try:
                    current_page = int(section_meta["page"])
                except ValueError:
                    current_page = None
            if section_meta.get("status"):
                current_status = section_meta["status"]
            if section_meta.get("keywords"):
                current_keywords = _split_keywords(section_meta["keywords"])
            if section_meta.get("citation"):
                current_citation = section_meta["citation"]
            if section_meta.get("source_url"):
                current_source_url = section_meta["source_url"]
            continue

        buffer.append(stripped)

    flush()
    return documents


_lock = threading.Lock()
_cache: list[KnowledgeDocument] | None = None
_cached_mtime: float | None = None


def _latest_mtime() -> float:
    files = list(KNOWLEDGE_DIR.rglob("*.md"))
    if not files:
        raise KnowledgeBaseError(f"知识库目录没有 .md 文件：{KNOWLEDGE_DIR}")
    return max(path.stat().st_mtime for path in files)


def load_documents() -> list[KnowledgeDocument]:
    """加载全部知识片段；任一文件变更时自动重载。"""
    global _cache, _cached_mtime
    mtime = _latest_mtime()
    with _lock:
        if _cache is not None and _cached_mtime == mtime:
            return _cache

        documents: list[KnowledgeDocument] = []
        for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
            if path.name == "README.md":
                continue
            documents.extend(_parse_file(path))

        if not documents:
            raise KnowledgeBaseError(f"知识库没有可用的知识片段：{KNOWLEDGE_DIR}")

        seen: set[str] = set()
        for document in documents:
            if document.id in seen:
                raise KnowledgeBaseError(f"知识片段 id 重复：{document.id}")
            seen.add(document.id)

        _cache = documents
        _cached_mtime = mtime
        return _cache


def searchable_text(document: KnowledgeDocument) -> tuple[str, str, str]:
    """返回（标题、关键词、正文）三段文本，供检索器加权。"""
    keywords = " ".join(document.keywords)
    return document.title, keywords, document.content


__all__ = [
    "BOOK_SOURCE",
    "KNOWLEDGE_DIR",
    "KnowledgeBaseError",
    "KnowledgeDocument",
    "load_documents",
    "searchable_text",
]
