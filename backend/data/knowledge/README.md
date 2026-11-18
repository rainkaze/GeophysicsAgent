# 知识库说明

本目录是本地 Agent 的知识库。**加一个 `.md` 文件，下一次请求即被索引**，无需登记清单。

## 目录结构

```
knowledge/
  book/                      教材《An Introduction to Geophysical Exploration》按章拆分
    01_principles.md           第 1 章 … 第 11 章
    12_appendix.md
    manifest.json              分章/页码/清洗统计（仅供溯源，检索器不读它）
  course/
    course_handouts.md         课程课件与外部权威来源的中文整理条目
  README.md                   本说明
```

- `book/` 是**英文原文**，带印刷页码标记 `[p.N]`，用于回引页码与逐页引用；
- `course/` 是**中文条目**，用于中文提问的召回（中文提问不会命中英文原文）。
- 由 `backend/scripts/build_book_knowledge.py` 从原 PDF 重新生成 `book/`。

## 如何添加新文件

把任何 Markdown 文件放进本目录（可建子目录），例如一份规范、一篇论文摘要或一段课件笔记：

```markdown
---
source: 《岩土工程勘察规范》GB 50021 条文
status: 已核对
keywords: 勘察阶段、钻孔间距、勘探点布置
---

# 我的新知识

## 3.2 勘察阶段划分

正文……
```

检索器会自动切分并建立混合检索索引（BM25 + 向量 + Rerank），字段加权为：标题 ×3、关键词 ×2、正文 ×1。

## 文件约定（均为可选）

| 写法 | 作用 |
|---|---|
| 文件顶部 `---` 之间的 `key: value` | 文件级 `source / status / keywords` |
| 正文里的 `[p.N]` | 印刷页码，成为该片段的引用页码 |
| `##` / `###` 小节 | 一个检索单元；标题即片段标题 |
| `## ID｜标题` | 同时给出稳定的知识条目编号（保留 `ID`） |
| `<!-- meta: source=... \| page=13 \| status=... -->` | 小节级元数据 |

## 重新生成教材分章

改了原 PDF 或清洗规则后：

```powershell
backend\.venv\Scripts\python.exe backend\scripts\build_book_knowledge.py
```

教材印刷页码 N 对应 PDF 第 N+13 页（已用页眉页码逐页核对）。
