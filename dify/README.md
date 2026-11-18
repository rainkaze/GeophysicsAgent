# Dify 侧实现（与本地同源）

这里放的是"同一套判据、第二种呈现"的全部材料：Dify 上跑的代码节点、提示词、
知识库导出脚本，以及证明两端一致的**对拍脚本**。

```
dify/
  README.md               ← 你在看这个
  setup.md                施工图：逐屏怎么配（含你现有配置的对错判定）
  prompts.md              LLM 节点提示词（唯一调用模型的地方）
  code_node_assess.py     代码节点①的可读版（1620 行，带注释，**不要直接粘**）
  code_node_assess_slim.py 代码节点①的粘贴版（511 行 / 48 KB，语义完全相同）← 粘这个
  build_slim.py           从可读版生成粘贴版，并自动对拍 882 组
  code_node_evidence.py   代码节点③：知识检索结果整理成证据清单
  code_node_finalize.py   代码节点②：14 条校验 + 兜底 + Markdown 渲染
  selftest.py             三个节点串起来的本地自测（不进 Dify）
  flow-map.png            Chatflow 搭建路线图（贴给用户照做的图）
  kb_export.py            把本地知识库导出成 Dify 专用分段文件（页码内联）
  knowledge/              ↑ 的产物，13 个文件 / 1337 个片段，直接上传
  parity_test.py          两端对拍：同输入必须同输出
```

## 和本地模块的对应关系

| 本地 | Dify | 一致性保证 |
|---|---|---|
| `agent/intake.py` | 代码① `extract_conditions` | 同一套正则与别名表，对拍 9 段文本 |
| `analysis/tables.py` + `catalog.py` | 代码① 的常量表 | **逐字搬运**，不是"精简版" |
| `analysis/calculator.py` | 代码① `assess` | 同一判定顺序、同一 f-string |
| `analysis/physics.py` | 代码① `design_*` | 同上（含 GPR 选频的两遍循环） |
| `analysis/design.py` | 代码① `build_design` | 同上 |
| `agent/verifier.py` | 代码② `verify` | 14 条规则逐条移植 |
| `agent/planner.fallback_plan` | 代码② `fallback_plan` | 同上 |
| `agent/renderer.py` | 代码② `render` | 同一张表结构、同一批数字 |
| `agent/session_store.py` | 会话变量 + `merge_conditions` | 合并语义相同 |
| `knowledge/corpus.py` | `kb_export.py` | 用**同一个解析器**切片段，只重排排版 |
| `knowledge/retriever.py` | Dify 混合检索（向量 + Rerank） | 算法不同，检索源相同（这一点答辩要主动说） |

> 检索算法不可能完全相同（本地是 BM25+向量 RRF → qwen3-rerank，Dify 是它自己的
> 混合检索）。所以两边"证据条目"未必逐条相同，但**评估与方案必须逐字段相同**——
> 那才是"数值不靠模型"的证明。

## 三条命令

```powershell
cd D:\QQDownload\研一上\工程地球物理概论\geophysics_agent_demo2

# 1) 生成要上传到 Dify 的知识库文件
backend\.venv\Scripts\python.exe dify\kb_export.py

# 2) 对拍：本地 analysis/ vs Dify 代码节点
backend\.venv\Scripts\python.exe dify\parity_test.py

# 3) 三个节点串起来自测（不需要 Dify，也不需要模型）
backend\.venv\Scripts\python.exe dify\selftest.py
```

## 对拍结果（当前）

```
评估矩阵：882 组 × 8 方法 × 19 字段；校验对拍 11 组草案；端到端 4 条路径
PARITY OK：两端逐字段一致
```

覆盖面：

- **条件抽取**：4 个内置场景 + 5 段刁钻文本（缺项、否定句、纯深度追问）
- **评估矩阵**：7 目标 × 7 介质 × 6 个埋深区间 × 3 种干扰组合 = 882 组，
  每组比对 8 个方法的 19 个字段（最大深度、余量、校核文案、适用性、理由、
  分辨率、分辨率依据、点距、排列长度、成本、物理依据、布设要求、限制、
  干扰说明、采集参数）＋ 推荐主辅、外业设计的 8 个字段
- **校验**：11 组草案（规则方案 / 主方法换成不可行方法 / 去掉 mitigation /
  验证措施不合格）逐条比对 14 条规则的 code + severity + message
- **多轮**：4 组追问的条件合并
- **端到端**：正常 / 坏草案降级 / 非 JSON 降级 / 条件不全追问

只要改动了本地 `analysis/` 或 `tables.py`，跑一次 `parity_test.py` 就知道
Dify 侧要不要跟着改——这是这个目录存在的真正理由。

## 两端同步 SOP（改了本地之后必做）

Dify 里存的是**你粘贴过去的副本**，它不会跟着本地文件变。所以每次改完本地，按这个顺序：

```powershell
# 1) 重新生成粘贴版（会自动对拍 882 组，语义不一致就报错）
backend\.venv\Scripts\python.exe dify\build_slim.py

# 2) 两端逐字段对拍（失败说明逻辑已经分叉，先修再往下走）
backend\.venv\Scripts\python.exe dify\parity_test.py
```

3) 回 Dify **重新粘贴**受影响的节点，点节点右上 ▶ 让它重跑；
4) 用那句改动相关的输入验证一下，然后 **发布**。

### 改哪个文件 → 要重粘哪个节点

| 改了本地 | 要重粘 Dify | 验证方法 |
|---|---|---|
| `analysis/tables.py`、`catalog.py`、`physics.py`、`design.py`、`calculator.py` | **代码①评估**（512 行） | 问一句场景，看方法比选表 |
| `agent/intake.py`（抽取规则）、追问文案（`renderer.render_clarification`） | **代码①评估** | 问"你是谁"，看是否出现自我介绍 |
| `agent/verifier.py`（14 条规则）、`planner.fallback_plan`、`renderer.render`（正文） | **代码②校验渲染**（336 行） | 故意把 SYSTEM 改坏，看是否降级 |
| `agent/prompts.py`（提示词） | **LLM 节点的 SYSTEM / USER** | 问一句，看 JSON 是否合法 |
| `backend/data/knowledge/**` | 跑 `kb_export.py` 后**重传知识库** | 召回测试看分块数 ≈ 1337 |
| 只改前端 / API 层 | 不需要动 Dify | — |

> **版本自检用 BUILD 指纹，不要用行号**（改动一次行数就会漂）：
> 三个节点文件末尾都有 `BUILD = "..."`。粘贴后 Ctrl+F 搜 `BUILD`：
> 搜到了且值一致 = 粘全了且是新版；搜不到 = 被截断或还是旧版。
> 改代码时记得同步更新这个值（`dify/build_slim.py` 的 `TAG` 常量决定它）。

## 已知差异（主动说明，别等人问）

1. **检索算法不同**（见上表）。答辩口径：同一套知识、两种检索方式交叉印证。
2. **Dify 侧没有"回灌修复"**：本地是 `verify → repair(≤1 次) → fallback`，
   Dify 是 `verify → fallback`。原因是 Chatflow 里做"带条件回边"循环很难讲清楚；
   效果上"不通过就不让它上场"是一样的，只是省了一次模型调用。
