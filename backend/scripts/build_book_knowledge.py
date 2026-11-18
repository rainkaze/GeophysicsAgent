"""把教材 PDF 预处理成按章拆分、带印刷页码标记的 Markdown，作为基础知识库。

只读输入文件，输出到 backend/data/knowledge/book/：

- 修复 PDF 抽出的连字（ﬁ/ﬂ）与跨行断词（exam-\\nple → example）；
- 去掉页眉页脚（书名、页码、Chapter N、章名+页码），含与正文粘连的情况；
- 补回抽丢的标点后空格（components.The → components. The）；
- 丢弃纯符号的公式碎片行（PDF 里排不成可读文本，留着只会稀释检索）；
- 按行块重排成段落，小节标题与图注各自成段；
- 每页前插入 [p.NN] 印刷页码标记，便于回答里回指页码；
- 章节边界来自书前目录（印刷页码）+ 固定偏移 13。

这是"可复现的数据加工"：改了 PDF 或清洗规则，重跑本脚本即可重建知识库。

用法：
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\build_book_knowledge.py
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = (
    ROOT / "backend" / "data" / "book" / "An Introduction to Geophysical Exploration.pdf"
)
DEFAULT_OUTPUT = ROOT / "backend" / "data" / "knowledge" / "book"

# 印刷页码 N 对应 PDF 第 N+13 页（已用页眉页码逐页核对）。
# PdfReader.pages 是 0 起始，索引 = 印刷页码 + PDF_OFFSET - 1。
PDF_OFFSET = 13
MAX_BLOCK = 750
BOOK_TITLE = "An Introduction to Geophysical Exploration"
BOOK_TITLE_ZH = "地球物理勘探导论"
EDITION = "3rd ed., Kearey, Brooks & Hill, 2002"

LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "ft",
    "\ufb06": "st",
    "\u00a0": " ",
    "\u2019": "'",
    "\u2018": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2010": "-",
    "\u2011": "-",
}

MATH_SYMBOLS = set("=∆ΔρσθφλμτψΩπΣ∑∫√∂≤≥±×÷·°≈≠~^±ÈÎÍ˘˚˙")

SECTION_HEADING = re.compile(r"^\d{1,2}(?:\.\d{1,2}){1,2}\s+[A-Z]\S?.{2,80}$")
CAPTION = re.compile(r"^(?:fig(?:ure)?\.|table|plate)\s*\d", re.IGNORECASE)
CHAPTER_HEADING = re.compile(r"^chapter\s+\d+\b", re.IGNORECASE)
BLOCK_STARTERS = {"problems", "further reading", "references", "index", "appendix"}
TERMINAL = '.!?:;)]"'
ABBREVIATIONS = (
    "Fig",
    "Figs",
    "Eq",
    "Eqs",
    "No",
    "Nos",
    "vs",
    "cf",
    "e.g",
    "i.e",
    "et al",
    "Dr",
    "ca",
)


@dataclass(frozen=True)
class Chapter:
    number: int
    title: str
    printed_start: int
    printed_end: int
    slug: str


CHAPTERS: tuple[Chapter, ...] = (
    Chapter(
        1, "The principles and limitations of geophysical exploration methods", 1, 7, "principles"
    ),
    Chapter(2, "Geophysical data processing", 8, 20, "data_processing"),
    Chapter(3, "Elements of seismic surveying", 21, 42, "seismic_elements"),
    Chapter(4, "Seismic reflection surveying", 43, 98, "seismic_reflection"),
    Chapter(5, "Seismic refraction surveying", 99, 124, "seismic_refraction"),
    Chapter(6, "Gravity surveying", 125, 154, "gravity"),
    Chapter(7, "Magnetic surveying", 155, 182, "magnetic"),
    Chapter(8, "Electrical surveying", 183, 207, "electrical"),
    Chapter(9, "Electromagnetic surveying", 208, 230, "electromagnetic"),
    Chapter(10, "Radiometric surveying", 231, 235, "radiometric"),
    Chapter(11, "Geophysical borehole logging", 236, 249, "borehole_logging"),
    Chapter(
        12, "Appendix: SI, c.g.s. and Imperial units and conversion factors", 250, 250, "appendix"
    ),
)

# 页眉里出现的章名（含第 1 章的短标题），用于两种粘连形态的清除：
#   "{页眉} 页码"（如 "Electrical surveying 183"）与 "{页码} {页眉}"（如 "8 Electrical surveying"）。
RUNNING_HEAD_TITLES: tuple[str, ...] = (
    "The principles and limitations of geophysical exploration methods",
    "Principles of Exploration Methods",
    "Geophysical data processing",
    "Elements of seismic surveying",
    "Seismic reflection surveying",
    "Seismic refraction surveying",
    "Gravity surveying",
    "Magnetic surveying",
    "Electrical surveying",
    "Electromagnetic surveying",
    "Radiometric surveying",
    "Geophysical borehole logging",
)


def _running_head_patterns() -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = [
        re.compile(r"\b\d{1,3}\s+Chapter\s+\d+"),
        re.compile(r"\bChapter\s+\d+\s+\d{1,3}\b"),
        re.compile(r"\b" + re.escape(BOOK_TITLE) + r"(?:\s+\d{1,3})?\b", re.IGNORECASE),
    ]
    for title in RUNNING_HEAD_TITLES:
        escaped = re.escape(title)
        patterns.append(re.compile(r"\b" + escaped + r"\s+\d{1,3}\b", re.IGNORECASE))
        patterns.append(re.compile(r"\b\d{1,3}\s+" + escaped + r"\b", re.IGNORECASE))
    return patterns


RUNNING_HEADS = _running_head_patterns()


@dataclass
class Stats:
    header_hits: int = 0
    math_dropped: int = 0
    ligatures: int = 0
    dehyphenated: int = 0
    spaces_fixed: int = 0
    paragraphs: int = 0
    extras: dict[str, int] = field(default_factory=dict)


def normalise(text: str, stats: Stats) -> str:
    for bad, good in LIGATURES.items():
        if bad in text:
            stats.ligatures += text.count(bad)
            text = text.replace(bad, good)
    text = text.replace("\r", "\n").replace("\t", " ")
    text = re.sub(r"[ \u2002-\u200a\u202f\u205f\u3000]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)

    for pattern in RUNNING_HEADS:
        text, hits = pattern.subn(" ", text)
        stats.header_hits += hits

    # PDF 里 "components.The" / "sec.,is" 这类标点后空格丢失
    def fix_space(match: re.Match[str]) -> str:
        prefix = match.group(1)
        punct = match.group(2)
        if any(prefix.endswith(abbr) for abbr in ABBREVIATIONS):
            return match.group(0)
        stats.spaces_fixed += 1
        return f"{prefix}{punct} {match.group(3)}"

    text = re.sub(r"(\b[A-Za-z][A-Za-z']*)([.,;:!?])([A-Za-z])", fix_space, text)
    text = text.replace("e. g.", "e.g.").replace("i. e.", "i.e.")
    text = re.sub(r"[ ]{2,}", " ", text)
    return text


def page_lines(raw: str, stats: Stats) -> list[str]:
    cleaned = normalise(raw, stats)
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]

    kept: list[str] = []
    for line in lines:
        if re.fullmatch(r"\d{1,3}", line):
            stats.header_hits += 1
            continue
        if line.lower() in {BOOK_TITLE.lower(), BOOK_TITLE_ZH}:
            stats.header_hits += 1
            continue
        letters = sum(ch.isalpha() for ch in line)
        symbols = sum(ch in MATH_SYMBOLS for ch in line)
        if symbols >= 2 and letters / max(len(line), 1) < 0.35:
            stats.math_dropped += 1
            continue
        kept.append(line)

    merged: list[str] = []
    for line in kept:
        previous = merged[-1] if merged else ""
        if previous.endswith("-") and line[:1].islower() and len(previous) > 2:
            merged[-1] = previous[:-1] + line
            stats.dehyphenated += 1
        else:
            merged.append(line)
    return merged


def starts_block(line: str) -> bool:
    if CHAPTER_HEADING.match(line) or CAPTION.match(line):
        return True
    if line.lower() in BLOCK_STARTERS:
        return True
    return bool(SECTION_HEADING.match(line)) and len(line) <= 85


def build_blocks(lines: list[str], stats: Stats) -> list[str]:
    """把硬换行的行流重排成段落：标题、图注、Problems 各自成段。"""
    blocks: list[str] = []
    current: list[str] = []
    caption_open = False

    def flush() -> None:
        if current:
            blocks.append(" ".join(current).strip())
            current.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        if starts_block(line):
            flush()
            caption_open = bool(CAPTION.match(line))
            block = line
            # 标题也可能被 PDF 折行：续行以小写开头时并回标题。
            while (
                not caption_open
                and index + 1 < len(lines)
                and lines[index + 1][:1].islower()
                and len(block) < 85
            ):
                index += 1
                block = f"{block} {lines[index]}".strip()
            blocks.append(block)
            stats.paragraphs += 1
            index += 1
            continue
        if caption_open:
            # 图注的续行（含图内标注）并进同一段，避免一句注被切成四五段。
            if blocks and not blocks[-1].endswith(TERMINAL):
                blocks[-1] = f"{blocks[-1]} {line}".strip()
                index += 1
                continue
            caption_open = False
        if current and current[-1].endswith("-") and line[:1].islower():
            current[-1] = current[-1][:-1] + line
            stats.dehyphenated += 1
        else:
            current.append(line)
        index += 1
    flush()
    return blocks


SENTENCE_END = re.compile(r"(?<=[.!?])[\"')\]]?\s+")


def split_long(block: str, limit: int = MAX_BLOCK) -> list[str]:
    """把超长段落按句子重新聚合成不超过 limit 的块，避免在句中切断。"""
    if len(block) <= limit:
        return [block]

    pieces: list[str] = []
    current = ""
    for sentence in SENTENCE_END.split(block):
        sentence = sentence.strip()
        if not sentence:
            continue
        if current and len(current) + len(sentence) + 1 > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
        while len(current) > limit:
            cut = current.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            pieces.append(current[:cut].strip())
            current = current[cut:].strip()
    if current:
        pieces.append(current)
    return pieces


def render_page(printed_page: int, blocks: list[str]) -> str:
    tag = f"[p.{printed_page}]"
    parts = [tag]
    first = True
    for block in blocks:
        for piece in split_long(block):
            if SECTION_HEADING.match(piece) and len(piece) <= 85:
                parts.append(f"### {piece}")
            elif first:
                parts.append(piece)
                first = False
            else:
                parts.append(f"{tag} {piece}")
    return "\n\n".join(parts)


def render_chapter(chapter: Chapter, reader: PdfReader, stats: Stats) -> str:
    pages = []
    for printed in range(chapter.printed_start, chapter.printed_end + 1):
        index = printed + PDF_OFFSET - 1
        if index >= len(reader.pages):
            raise IndexError(f"印刷页 {printed} 超出 PDF 范围（共 {len(reader.pages)} 页）")
        raw = reader.pages[index].extract_text() or ""
        pages.append(render_page(printed, build_blocks(page_lines(raw, stats), stats)))

    heading = f"# {chapter.number} {chapter.title}"
    note = (
        f"> {BOOK_TITLE}（{BOOK_TITLE_ZH}，{EDITION}）第 {chapter.number} 章，"
        f"印刷页 {chapter.printed_start}–{chapter.printed_end}。\n"
        f"> 页码标记 [p.N] 指书的印刷页码（PDF 页码 = 印刷页码 + {PDF_OFFSET}）。"
    )
    return "\n\n".join([heading, note, *pages]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    reader = PdfReader(args.source)
    args.output.mkdir(parents=True, exist_ok=True)

    manifest = []
    stats = Stats()
    total_chars = 0
    for chapter in CHAPTERS:
        text = render_chapter(chapter, reader, stats)
        name = f"{chapter.number:02d}_{chapter.slug}.md"
        destination = args.output / name
        destination.write_text(text, encoding="utf-8")
        chars = len(re.sub(r"\s+", "", text))
        total_chars += chars
        manifest.append(
            {
                "file": name,
                "chapter": chapter.number,
                "title": chapter.title,
                "printed_pages": [chapter.printed_start, chapter.printed_end],
                "page_markers": len(re.findall(r"^\[p\.\d+\]$", text, re.MULTILINE)),
                "chars": chars,
            }
        )
        print(f"{name:32s} p.{chapter.printed_start:>3}-{chapter.printed_end:<3} {chars:>7} 字符")

    summary = {
        "source": str(args.source),
        "output": str(args.output),
        "chapters": manifest,
        "total_chars": total_chars,
        "total_page_markers": sum(item["page_markers"] for item in manifest),
        "cleaning": {
            "ligatures_fixed": stats.ligatures,
            "running_head_hits": stats.header_hits,
            "math_fragments_dropped": stats.math_dropped,
            "line_hyphens_joined": stats.dehyphenated,
            "missing_spaces_fixed": stats.spaces_fixed,
        },
    }
    (args.output / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n合计 {total_chars} 字符，{summary['total_page_markers']} 个页码标记")
    print(json.dumps(summary["cleaning"], ensure_ascii=False))


if __name__ == "__main__":
    main()
