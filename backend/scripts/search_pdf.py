"""在可抽取文字的 PDF 中按关键词定位页码，供人工核对知识条目。"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("keywords", nargs="+")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    reader = PdfReader(args.pdf)
    results = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if any(word.casefold() in text.casefold() for word in args.keywords):
            results.append(
                {
                    "pdf_page": page_number,
                    "text_preview": " ".join(text.split())[:900],
                }
            )
            if len(results) >= args.limit:
                break
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
