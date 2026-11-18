# Dify 对齐指南（原理篇）

> 具体怎么点、每个参数填什么，见 [`dify/setup.md`](../dify/setup.md)。
> 这篇只讲**为什么这样对齐**，以及"两种呈现"在答辩时怎么说。

## 1. 两种呈现，一套判据

| | 本地（本项目） | Dify（平台侧） |
|---|---|---|
| 形态 | Vue3 + FastAPI，本地跑 | 工作室 → **Chatflow** |
| 条件抽取 | `agent/intake.py` 规则 | 代码节点① `extract_conditions` |
| 八方法评估 | `analysis/`（Python） | 代码节点①（同一批表的逐行移植） |
| 检索 | BM25 + text-embedding-v4 + qwen3-rerank | 混合检索 + qwen3-rerank |
| 方案生成 | LLM 选角色 + 写理由 | LLM 节点（同一份提示词） |
| 自检 | 14 条规则 + 回灌修复 | 代码节点②：14 条规则 + 换规则方案 |
| 外业设计 | `analysis/design.py` | 代码节点① `build_design` |
| 正文渲染 | `agent/renderer.py` | 代码节点② `render` |

两边**互不调用**，靠三件事保证一致：

1. **判据同源**：代码节点不是"精简版"，是 `tables.py` / `calculator.py` / `physics.py`
   的逐行移植（连 f-string 格式都一样）。
2. **知识同源**：`dify/kb_export.py` 用**同一个解析器**切片段，只是把
   `[p.N]` 与 `<!-- meta -->` 改写成片段首行的可见元数据——正文一字不改。
3. **可验证**：`dify/parity_test.py` 跑 882 组条件、11 组草案、4 条端到端路径，
   逐字段比对。不一致就打印出来。

## 2. 为什么必须是 Chatflow，不能是 Agent 应用

Agent 应用（"通过对话构建 Agent"）没有代码节点。没有代码节点，八方法评估就只能
让模型在自然语言里"算"，于是：

- 同一个场景问两次，电极距、排列长度可能不一样；
- 本地和 Dify 的数字对不上，答辩时无法回答"哪个是对的"；
- "数值不靠模型"这个核心卖点，在 Dify 侧不存在。

Chatflow 里可以放 Python 代码节点，才能把"确定性计算"搬过去。
（Agent 应用可以留着当反例演示，但主呈现用 Chatflow。）

## 3. 知识库分段：为什么不能直接用原始 `.md`

本地知识库的排版是给**本地解析器**用的：

- `[p.N]` **独占一行** → 解析器把它读成"接下来这段属于第 N 页"，且不进正文；
- `<!-- meta: source=... | page=... -->` → 不可见注释；
- `## 标题` → 片段标题（教材 12 章其实只有 `#`，没有 `##`）。

Dify 的通用分段只认"分段标识符"，不认这些约定。若用 `\n` 当分隔符，
每个页码行都会变成独立碎块（用户截图里就有一个 7 字符的 `Chunk-4`），
页码与正文彻底脱钩。

所以 `dify/kb_export.py` 做了一次等价转换：

```
08_electrical#80｜8.2.10 Applications of resistivity surveying｜《An Introduction…》｜p.196｜教材原文
[p.196] Resistivity surveying is applied to a wide range of ...
```

首行 = 编号｜标题｜出处｜页码｜核对状态，正文前带 `[p.196]`。
用 `\n\n` 分段时，**一个片段 = 本地一个片段 = 1337 个块**，页码跟着片断一起被检索到。

> 关于标题层级：教材每章是 1 个 `#` 章标题 + 若干 `###` 小节标题（`##` 一个都没有），
> `course_handouts.md` 用 `##`。所以"Markdown 分段"其实也能切，但我们仍用"通用 + 空行"，
> 因为只有这样才能保证**一块 = 本地一个片段**（实测 `01_principles.md` 得到 39 块，
> 恰好等于本地解析出的 39 个片段）。`###` 被当作片段标题保留在首行，检索时能落到小节级别。

## 4. 代码节点

| 文件 | 作用 | 关键接口 |
|---|---|---|
| `dify/code_node_assess.py` | 条件抽取 + 八方法评估 + 外业设计 | `main(query, prev_conditions) -> dict` |
| `dify/code_node_evidence.py` | 知识检索结果 → 证据清单 | `main(result) -> dict` |
| `dify/code_node_finalize.py` | 14 条校验 + 兜底 + 渲染 | `main(assess_json, llm_json, evidence) -> dict` |

三个节点都**只用 json / math / re**，因为 Dify 代码沙箱没有第三方库。

本地自测（不需要 Dify）：

```powershell
backend\.venv\Scripts\python.exe dify\code_node_assess.py     # 看四个示例场景
backend\.venv\Scripts\python.exe dify\parity_test.py          # 两端对拍
```

## 5. 答辩口径（三句话）

1. "**同一套判据、两种呈现**：本地 Python 和 Dify 代码节点共用一批判据表，
   882 组条件逐字段对拍通过。"
2. "**检索算法不同，检索源相同**：本地是 BM25+向量 RRF → 重排，Dify 是它自己的
   混合检索，两边知识库来自同一批文件，可以交叉印证。"
3. "**模型在两边都只做选择题**：数字进不了正文，因为正文是代码节点渲染的。"

## 6. 已知差异（主动说明，别等人问）

| 差异 | 原因 | 说法 |
|---|---|---|
| 检索算法不同 | 平台实现不可控 | 同一批知识、两种检索方式交叉印证 |
| Dify 侧没有"回灌修复" | Chatflow 里做带条件回边循环不好讲 | 本地 `verify→repair→fallback`，Dify `verify→fallback`，效果都是"不通过就不上场" |
| Dify 侧多轮用会话变量 | 平台机制不同 | 合并语义与本地 `SiteConditions.merge` 相同（已对拍） |
