"""将同一份知识 JSON 导出为可上传到 Dify 的 Markdown 文档。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend" / "data" / "knowledge" / "course_knowledge.json"
OUTPUT = ROOT / "backend" / "data" / "knowledge" / "dify_knowledge.md"


def main() -> None:
    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    chunks = ["# 工程物探课程与参考知识库", ""]
    for record in records:
        chunks.extend(
            [
                f"## {record['id']}｜{record['title']}",
                "",
                record["content"],
                "",
                f"- 来源：{record['source']}",
                f"- 页码：{record.get('page') or '未标注'}",
                f"- 状态：{record['verification_status']}",
                f"- 引用：{record.get('citation') or '无'}",
                f"- 关键词：{'、'.join(record.get('keywords', []))}",
                f"- URL：{record.get('source_url') or '无'}",
                "",
            ]
        )
    OUTPUT.write_text("\n".join(chunks), encoding="utf-8")
    print(f"已导出 {len(records)} 条知识到：{OUTPUT}")


if __name__ == "__main__":
    main()
