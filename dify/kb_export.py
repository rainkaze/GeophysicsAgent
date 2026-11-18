# -*- coding: utf-8 -*-
"""把本地知识库导出为 **Dify 专用分段文件**（内容逐字不变，只重排排版）。

为什么需要这一步
----------------
本地 `knowledge/corpus.py` 是按"文件约定"解析的：

- `[p.N]` 独占一行 → 作为其后正文的页码，**不进正文**；
- `<!-- meta: ... -->` → 一条不可见注释，携带来源/页码/核对状态；
- `## 标题` → 片段标题。

Dify 的通用分段只认"分段标识符"，不认这些约定。直接上传原始 `.md`：

1. 以 `\\n` 分段时，`[p.250]` 这种页码行会**单独变成 7 个字符的碎块**，
   正文与页码彻底脱钩——"可回引页码"这个卖点就没了；
2. `<!-- meta: ... -->` 会被当作正文一起索引，既占 token 又不像正文；
3. 教材每章是 1 个 `#` 章标题 + 若干 `###` 小节标题，`##` 没有——直接用"通用分段"
   时，标题行会被切成独立的短块，正文与标题脱钩。

因此这里做一次**等价转换**：仍然用本地解析器切出的同一批片段（同一批文字、
同一个页码），但把元数据写成**可见的片段首行**，片段之间用一个空行分隔。
这样 Dify 用 `\\n\\n` 分段时，一个片段 = 本地一个片段，页码与出处随片段一起被检索到。

跑法
----
    cd geophysics_agent_demo2
    backend\\.venv\\Scripts\\python.exe dify\\kb_export.py

产物：`dify/knowledge/*.md`（直接拖进 Dify 知识库）
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from geophysics_agent.core.config import BACKEND_ROOT  # noqa: E402
from geophysics_agent.knowledge.corpus import KNOWLEDGE_DIR, load_documents  # noqa: E402

OUT_DIR = ROOT / "dify" / "knowledge"


def _source_stem(path: Path) -> str:
    return path.stem


BOOK_LABEL = "《An Introduction to Geophysical Exploration》(3rd ed., 2002)"
BOOK_STATUS_SHORT = "教材原文"


def _header(document) -> str:
    """片段首行：id｜标题｜来源与页码｜核对状态（外部来源再附链接）。"""
    is_book = "#" in document.id
    parts = [document.id, document.title]
    if is_book:
        parts.append(BOOK_LABEL)
        if document.page is not None:
            parts.append(f"p.{document.page}")
        parts.append(BOOK_STATUS_SHORT)
    else:
        if document.citation:
            parts.append(document.citation.rstrip("."))
        else:
            parts.append(document.source)
        parts.append(document.status)
    if document.source_url:
        parts.append(document.source_url)
    return "｜".join(part for part in parts if part)


def _clean(text: str) -> str:
    """片段内部不允许出现空行，否则会被 Dify 判成两个片段。"""
    return " ".join(text.split())


def _body(document) -> str:
    text = _clean(document.content)
    if document.page is None:
        return text
    # 少数行里 "[p.N]" 与正文挤在同一行（教材附录），避免重复加前缀
    if text.startswith(f"[p.{document.page}]"):
        return text
    return f"[p.{document.page}] {text}"


def main() -> int:
    documents = load_documents()

    grouped: dict[str, list] = {}
    for document in documents:
        # 用 id 前缀反查所属文件：book 片段 id 形如 "08_electrical#81"
        key = document.id.split("#")[0] if "#" in document.id else "course_handouts"
        grouped.setdefault(key, []).append(document)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUT_DIR.glob("*.md"):
        stale.unlink()

    total = 0
    longest = 0
    for stem in sorted(grouped):
        segments = []
        for document in grouped[stem]:
            segment = f"{_header(document)}\n{_body(document)}"
            longest = max(longest, len(segment))
            segments.append(segment)
        target = OUT_DIR / f"{stem}.md"
        # 片段之间恰好一个空行 → Dify 用 "\n\n" 分段时一段一块
        target.write_text("\n\n".join(segments) + "\n", encoding="utf-8")
        total += len(segments)
        print(f"  {target.name:28s} 片段 {len(segments):4d} 个")

    print()
    print(f"知识源：{KNOWLEDGE_DIR.relative_to(BACKEND_ROOT.parent)}")
    print(f"导出：{OUT_DIR}")
    print(f"片段总数：{total}（Dify 预期分块数 ≈ {total}）")
    print(f"最长片段：{longest} 字符 → Dify「分段最大长度」设为 1024 即可，不会二次硬切")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
