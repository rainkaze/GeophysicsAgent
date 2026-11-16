"""查看 PDF 页数和文本抽取覆盖率，不修改输入文件。"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)


def inspect(path: Path) -> dict[str, object]:
    reader = PdfReader(path)
    page_lengths = [len((page.extract_text() or "").strip()) for page in reader.pages]
    return {
        "file": path.name,
        "pages": len(reader.pages),
        "pages_with_text": sum(length > 0 for length in page_lengths),
        "pages_without_text": sum(length == 0 for length in page_lengths),
        "characters_extracted": sum(page_lengths),
        "sample_first_page_chars": page_lengths[0] if page_lengths else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="要检查的 PDF 文件或目录")
    args = parser.parse_args()
    pdfs = [
        child
        for path in args.paths
        for child in ([path] if path.is_file() else path.rglob("*.pdf"))
        if child.is_file() and child.suffix.lower() == ".pdf"
    ]
    print(json.dumps([inspect(path) for path in pdfs], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
