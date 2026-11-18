
# -*- coding: utf-8 -*-
"""Dify 代码节点③：把知识检索结果整理成**紧凑证据清单**。

为什么需要
----------
知识检索节点输出的是 `Array[Object]`（每项含 content / score / metadata…）。
直接塞进 LLM 提示词会有两个问题：一是 JSON 外壳和元数据字段很占 token，
二是模型容易把 `score` 当成"可信度"来用。

这里把每条证据压成一行：`id｜标题｜出处｜p.N` + 正文 + 相关度。
Dify 知识库里的片段首行已经写成 `id｜标题｜来源｜p.N`（见 `kb_export.py`），
所以模型在写 rationale 时可以直接回引 `（见 ERT-001, p.5）`，与本地一致。

输出变量：
    evidence_text  String   给 LLM 节点用的证据清单（无命中时说明"未检索到"）
    evidence_json  String   给最终渲染用的精简 JSON
"""

import json


def _normalize(result):
    if result is None:
        return []
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return []
    if isinstance(result, dict):
        result = result.get("result", [])
    items = []
    for item in result or []:
        if isinstance(item, dict):
            items.append(
                {
                    "content": str(item.get("content") or ""),
                    "score": item.get("score") if isinstance(item.get("score"), (int, float)) else None,
                    "title": str(item.get("title") or ""),
                }
            )
    return items


def _headline(content: str) -> tuple[str, str]:
    """片段首行是 `id｜标题｜来源｜p.N`，把它单独拿出来做引用行。"""
    first, _, rest = content.partition("\n")
    if "｜" in first and len(first) < 200:
        return first, rest
    return "", content


def main(result=None) -> dict:
    items = _normalize(result)
    if not items:
        text = "（本次未检索到课程知识条目，不得虚构编号或页码）"
        return {"evidence_text": text, "evidence_json": "[]"}

    lines = []
    for index, item in enumerate(items, start=1):
        headline, body = _headline(item["content"])
        score = f"（相关度 {item['score']:.2f}）" if item["score"] is not None else ""
        body = " ".join(body.split())
        lines.append(f"{index}. {headline}\n   {body[:400]}{'…' if len(body) > 400 else ''}{score}")

    return {
        "evidence_text": "\n".join(lines),
        "evidence_json": json.dumps(items, ensure_ascii=False),
    }


# 版本指纹（放末尾：既认版本，也能判断有没有粘全）
BUILD = "2026-11-17.2"
