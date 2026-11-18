# 知识库维护

知识库就是 `backend/data/knowledge/` 下的若干个 Markdown 文件。**加一个 `.md` 文件，下一次请求即被检索**，无需登记清单，也不用改代码。

## 目录与内容

| 路径 | 内容 | 语言/用途 |
|---|---|---|
| `book/*.md` | 教材《An Introduction to Geophysical Exploration》12 章全文，带 `[p.N]` 印刷页码 | 英文原文，用于回引页码 |
| `course/course_handouts.md` | 课程课件与外部权威来源的 17 条中文条目 | 中文，用于中文提问召回 |
| `README.md` | 格式说明（本目录内的说明，检索器自动跳过） | — |

中文提问不会命中英文原文，所以 `course/` 里的中文条目是中文场景召回的主要来源；
`book/` 的英文原文负责给出"哪一页说的"。

## 分章是否切分正确

章节边界已用 PDF 书签逐章核对：印刷页码 N 对应 PDF 第 N+13 页，
12 章的起止页与书前目录完全一致（第 1 章 p.1–7，第 2 章 p.8–20，…，第 11 章 p.236–249，附录 p.250）。
`book/manifest.json` 记录了每章页码范围与清洗统计，供溯源。

## 如何添加新文件

把任何 Markdown 文件放进本目录（可建子目录），例如一份规范、一篇论文摘要：

```markdown
---
source: 《岩土工程勘察规范》GB 50021
status: 已核对
keywords: 勘察阶段、钻孔间距、勘探点布置
---

# 勘察阶段划分

## 3.2 阶段划分

正文……
```

检索器自动切分并建立混合检索索引（BM25 + 向量 + Rerank），字段加权：标题 ×3、关键词 ×2、正文 ×1。

## 文件约定（均为可选）

| 写法 | 作用 |
|---|---|
| 文件顶部 `---` 之间 `key: value` | 文件级 `source / status / keywords` |
| 正文里的 `[p.N]` | 印刷页码，成为片段引用页码 |
| `##` / `###` 小节 | 一个检索单元，标题即片段标题 |
| `## ID｜标题` | 同时给出稳定编号（保留 `ID`，如 `ERT-001`） |
| `<!-- meta: source=... \| page=13 \| status=... -->` | 小节级元数据（覆盖文件级） |

## 重新生成教材分章

改了原 PDF 或清洗规则后重跑：

```powershell
backend\.venv\Scripts\python.exe backend\scripts\build_book_knowledge.py
```

脚本会修复连字、跨行断词、去掉页眉页脚、丢弃公式碎片行、按段落重排并插入 `[p.N]` 页码标记。

## 给 Dify 用：导出专用分段文件

本地这套 `.md` 的排版是给本地解析器看的（`[p.N]` 独占一行、`<!-- meta -->` 不可见）。
Dify 的通用分段不认这些约定，直接上传会把页码切成碎块。因此另有一份导出：

```powershell
backend\.venv\Scripts\python.exe dify\kb_export.py
```

它用**同一个解析器**切片段，只把元数据改写成片段首行：

```
08_electrical#80｜8.2.10 Applications of resistivity surveying｜《An Introduction…》｜p.196｜教材原文
[p.196] 正文……
```

产物在 `dify/knowledge/`（13 文件 / 1337 片段），上传到 Dify 时用
「通用 + 分隔符 `\n\n` + 最大长度 1024 + 重叠 150」。详见 `dify/setup.md`。

## 检索如何工作

`knowledge/retriever.py` 使用混合检索（配置了 DashScope key 时：BM25 + 向量 RRF 融合 → Rerank 重排；无 key 自动回退 BM25）：

- 中文按**二元组**切分，英文按词切分，过滤功能词；
- 字段加权：标题 ×3、关键词 ×2、正文 ×1；
- IDF 让"工程""物探"这类高频词自动降权；
- 输出 `matched_terms` 与 `score`，相关性分 `strong / weak / empty`，弱相关会提示"引用前请人工核对"。

检索命中只表示文本相关，不表示来源已验证或结论适用于具体工程。
