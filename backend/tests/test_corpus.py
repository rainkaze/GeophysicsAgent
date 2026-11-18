"""知识库加载测试：目录扫描、元数据解析与"添加文件即生效"。"""

from __future__ import annotations

from geophysics_agent.knowledge import corpus
from geophysics_agent.knowledge.corpus import KnowledgeBaseError, load_documents


def test_loads_book_and_course_documents() -> None:
    docs = load_documents()
    ids = {doc.id for doc in docs}

    # 教材英文原文（book/）与中文补充条目（course/）都应被扫描到
    assert any(doc.source.startswith("An Introduction") for doc in docs)
    assert "ERT-001" in ids
    assert "01_principles#1" in ids

    erd = next(doc for doc in docs if doc.id == "ERT-001")
    assert erd.page == 5
    assert erd.status
    assert "直流电阻率" in erd.title


def test_adding_a_markdown_file_is_indexed(tmp_path, monkeypatch) -> None:
    """模拟"上传一个文件即被索引"。"""
    monkeypatch.setattr(corpus, "KNOWLEDGE_DIR", tmp_path)
    monkeypatch.setattr(corpus, "_cache", None)
    monkeypatch.setattr(corpus, "_cached_mtime", None)

    target = tmp_path / "notes" / "example.md"
    target.parent.mkdir()
    target.write_text(
        """---
source: 测试规范
status: 已核对
keywords: 电阻率、ERT
---

# 测试知识

## TEST-001｜直流电阻率的多解性

<!-- meta: page=13 | citation=测试规范, p.13 -->

直流电阻率反演存在非唯一性，需要地质资料约束。
""",
        encoding="utf-8",
    )

    docs = load_documents()

    ids = {doc.id for doc in docs}
    assert "TEST-001" in ids
    test_doc = next(doc for doc in docs if doc.id == "TEST-001")
    assert test_doc.page == 13
    assert test_doc.source == "测试规范"
    assert test_doc.status == "已核对"
    assert "电阻率" in test_doc.keywords
    assert test_doc.citation == "测试规范, p.13"


def test_empty_knowledge_dir_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(corpus, "KNOWLEDGE_DIR", tmp_path)
    monkeypatch.setattr(corpus, "_cache", None)
    monkeypatch.setattr(corpus, "_cached_mtime", None)

    try:
        load_documents()
    except KnowledgeBaseError:
        return
    raise AssertionError("空知识库目录应当抛出 KnowledgeBaseError")
