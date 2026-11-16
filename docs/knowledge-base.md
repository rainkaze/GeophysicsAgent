# 知识库维护

知识库文件为 `backend/data/knowledge/course_knowledge.json`，每条记录需包含：

| 字段 | 说明 |
|---|---|
| `id` | 稳定编号，前缀表示来源类型（`GPR-`、`ERT-`、`BOOK-`、`EXT-`、`PAPER-`） |
| `title` / `content` | 标题与正文；正文用于检索与展示 |
| `source` | 来源文件名或文献名 |
| `page` | PDF 页码；无法核实填 `null` |
| `verification_status` | 核对状态，未人工核对的一律写"待人工核对" |
| `keywords` | 关键词，参与 BM25 加权检索 |
| `citation` / `source_url` | 规范引用与外部链接（可选） |

## 检索如何工作

`knowledge/retriever.py` 使用 BM25：

- 中文按**二元组**切分，英文按词切分，过滤功能词；
- 字段加权：标题 ×3、关键词 ×2、正文 ×1；
- IDF 让"工程""物探"这类到处出现的词自动降权；
- 输出 `matched_terms`（命中了哪些词）与 `score`，前端据此显示相关性；
- 相关性分为 `strong / weak / empty`，弱相关会明确提示"引用前请人工核对"。

因此**新增条目比调参更有效**：目前 17 条知识覆盖不到磁法、DAS、面波与
溶洞/污染羽/液化等目标，检索容易退化到泛化条目。补充条目时优先覆盖
"方法 × 目标"的组合（每种方法至少要有一条讲清它对某类目标的适用性与限制）。

## 新增条目的流程

1. 回到对应 PDF，用 `backend/scripts/search_pdf.py` 定位页码：
   ```powershell
   backend\.venv\Scripts\python.exe backend\scripts\search_pdf.py backend\data\PPT\F054Lect20261021DCERTIPfinal.pdf 电阻率 装置
   ```
2. 把原文结论整理成 1~3 句 `content`，附上 `source` 与 `page`；
3. `verification_status` 先写"待人工核对"，只有本人对照原文后才能改成"已核对"；
4. 跑 `pytest tests/test_retriever.py`，确认新条目能被相关提问召回。

检索命中只表示文本相关，不表示来源已验证或结论适用于具体工程。
