# Dify 施工图：从你现在这个应用，改成"和本地逐字段一致"的 Chatflow

> 目标：Dify 侧**独立**跑出和本地一样的方案——同样的八方法比选、同样的采集参数、
> 同样的外业工作量、同样的校验与降级。两边不互相调用，靠"同源判据 + 对拍脚本"保证一致。

---

## 0. 先判你截图里已配置的东西（结论）

| 你现在的配置 | 判定 | 原因 | 怎么改 |
|---|---|---|---|
| 应用类型：**Agent（对话式构建）** | ❌ 方向错 | Agent 应用里**没有代码节点**，八方法评估只能由模型"嘴上算"，两个呈现的数字必然不一致；且它和你自己的 `docs/dify-alignment.md`（"用工作室/Chatflow，不用 Agent"）矛盾 | 新建一个 **Chatflow** 应用（见 §2） |
| 模型 `deepseek-v4-flash` | ✅ 对 | 与本地 `deepseek-flash` 同源 | 温度改 **0** |
| 提示词：**空** | ❌ 没配 | 截图里还是"在此编写指令" | 粘贴 `dify/prompts.md`（见 §5） |
| SKILL / 文件 / 工具：全空 | ⭕ 可以空 | 这三项是 Agent 应用的能力，Chatflow 里没有也不影响 | 不用管 |
| 知识库 `工程地球物理概论 - 课程知识库` | ⚠️ 半对 | 12 个文档＝教材 12 章 ✅，但**漏了 `course_handouts.md`（17 条中文条目）**——中文提问的主要召回源 | 用 `dify/knowledge/` 的 13 个文件重建（见 §3） |
| 分段：**通用 + 分段标识符 `\n`** | ❌ 错，影响最大 | 见下面那张分块预览：`Chunk-4` 只有 **7 个字符**（只有 `[p.250]`），`Chunk-3` 39、`Chunk-5` 49。等于把"页码"和"正文"切成了两半——你项目最大的卖点"可回引页码"在 Dify 侧直接失效 | 换成 `\n\n` + 用导出文件重建（见 §3） |
| 分段最大长度 1024 / 重叠 150 | ✅ 数值对，但没生效 | 以 `\n` 切分后每段都很短，1024 几乎轮不到 | 换了分隔符后才有意义：**1024 / 150** |
| 索引方式：高质量 + `text-embedding-v4` | ✅ 对 | 与本地 `.env` 的 `EMBEDDING_MODEL=text-embedding-v4` 完全一致（实测 embedding 1024 维可用） | 保持 |
| 检索：混合检索 + Rerank `qwen3-rerank` | ✅ 对 | 与本地 `retriever.py` 的"BM25+向量 RRF → qwen3-rerank"同源 | 保持 |
| Top K = 8 | ⚠️ 与本地不一致 | 本地 `.env` 是 `KNOWLEDGE_TOP_K=5` | 二选一：把本地改成 8（推荐，证据更足），或把 Dify 改 5 |
| Score 阈值 = **0.7** | ❌ 错，会让检索结果全军覆没 | 实测：用真实片段 + 你的 4 个演示场景去打分，qwen3-rerank 的最高分只有 **0.55 / 0.62 / 0.65 / 0.66**（见 §3.4 实测表）。阈值 0.7 会把**所有**片段过滤掉，LLM 拿到的证据永远是空 | 改成 **0（关闭）** 或 0.3 |
| "有未发布的更改 · 4 小时前" | ❌ 没生效 | 知识库页面显示"12 文档 / **0 个关联应用**"，说明这次关联还停留在草稿；点「发布更新」之前，访问入口和 API 跑的还是旧版本 | 每次改完点 **发布更新** |

---

## 1. 为什么必须是 Chatflow 而不是 Agent

| | Agent 应用（你现在建的） | Chatflow（要改成的） |
|---|---|---|
| 能否嵌入 Python 代码节点 | **不能** | 能（就是本地 `analysis/` 的移植） |
| 数值由谁给 | 模型自己算 | 代码节点算 |
| 两次运行是否可复现 | 不可 | 可（温度 0 + 确定性代码） |
| 能否讲"校验 → 兜底" | 讲不了 | 能（第二个代码节点） |
| 答辩时能不能对上本地 | 对不上 | 能逐字段对上（`dify/parity_test.py`） |

保留 Agent 那个应用也没坏处——它可以当"对话式构建"的反例演示：
"如果只让模型自己算，它给出的电极距每次都不一样"。但**主呈现必须是 Chatflow**。

---

## 2. 新建 Chatflow

工作室 → 创建空白应用 → **Chatflow**（不是"工作流"：工作流没有会话变量，多轮追问做不了）。

目标流程图（6 个节点）：

```
开始
 └─▶ 代码①「八方法评估」  code_node_assess.py
       ├─ status == "need_more_info" ─▶ 直接回复（追问）  {{#assess.clarification_md#}}
       └─ 否则
            ├─▶ 知识检索（挂课程知识库）
            │     └─▶ 代码③「证据整理」 code_node_evidence.py
            │           └─▶ LLM「方案决策」  prompts.md
            └─▶ 代码②「校验+兜底+渲染」 code_node_finalize.py
                  └─▶ 直接回复   {{#finalize.answer_md#}}
```

> 代码② 同时接收 `assess.assess_json`、`llm.text`、`knowledge.result`，
> 所以 LLM 节点可以并行挂在检索后面，最后统一汇入代码②。

---

## 3. 知识库重建（这一步决定检索质量）

### 3.1 先生成 Dify 专用文件

```powershell
cd D:\QQDownload\研一上\工程地球物理概论\geophysics_agent_demo2
backend\.venv\Scripts\python.exe dify\kb_export.py
```

产物在 `dify/knowledge/`，13 个文件、**1337 个片段**——和本地解析器切出来的片段数
一模一样（同一个解析器，同一批文字，只是把 `[p.N]` 和 `<!-- meta -->` 改写成可见首行）。

一个片段长这样：

```
08_electrical#80｜8.2.10 Applications of resistivity surveying｜《An Introduction to Geophysical Exploration》(3rd ed., 2002)｜p.196｜教材原文
[p.196] Resistivity surveying is applied to a wide range of ...
```

首行就是"编号｜标题｜出处｜页码｜核对状态"，Dify 检索命中后原样喂给 LLM，
模型就能写「（见 08_electrical#80, p.196）」，和本地的引用格式一致。

### 3.2 上传与分段参数

知识库 → 新建 → 上传 `dify/knowledge/*.md`（13 个）→ 分段设置：

| 项 | 填什么 |
|---|---|
| 分段模式 | **通用** |
| 分段标识符 | **`\n\n`**（空行）← 关键 |
| 分段最大长度 | **1024** |
| 分段重叠长度 | **150** |
| 替换掉连续的空格、换行符和制表符 | ☑️ 勾 |
| 删除所有 URL 和电子邮件地址 | ☐ 不勾（我们的片段里带 EPA/USGS 链接，要留着可核对） |

预期结果：**索引完成后分块数 ≈ 1337**（导出脚本已保证最长片段 916 字符，不会被二次硬切）。
如果分块数明显少于 1337，说明 Dify 在合并相邻段——把「分段最大长度」调到 400 再试。

### 3.3 索引与检索

| 项 | 填什么 | 与本地对应 |
|---|---|---|
| 索引方式 | 高质量 | 本地走 text-embedding-v4 |
| Embedding 模型 | `text-embedding-v4` | `.env` 的 `EMBEDDING_MODEL` |
| 检索设置 | 混合检索 | `retriever.py` 的 BM25+向量 RRF |
| 权重设置 / Rerank 模型 | 选 **Rerank 模型** = `qwen3-rerank` | `.env` 的 `RERANK_MODEL` |
| Top K | **8**（并把本地 `.env` 的 `KNOWLEDGE_TOP_K` 也改成 8） | 两端同 K |
| Score 阈值 | **0（关闭）**，或 0.3 | 见 3.4 实测 |

### 3.4 为什么 0.7 必须关掉（实测）

用 `qwen3-rerank` 对你 4 个演示场景（都是多条件长句）分别和真实片段打分：

| 场景 | 最高 rerank 分 |
|---|---|
| 1 厚黏土追踪污染羽 | **0.623** |
| 2 城市浅层找管线 | **0.660** |
| 3 软土液化判别 | **0.555** |
| 4 山区路基找溶洞 | **0.649** |
| （对照）短查询"电阻率反演非唯一性" | **0.951** |

结论：**这个 reranker 的输出尺度整体偏低**，长场景描述的 top1 就在 0.55–0.66。
阈值 0.7 会让上面 4 个场景**一条证据都留不下**。要么关掉阈值，要么设 0.3。

> 这也顺便回答了"检索效果为什么一般"：真正的瓶颈不是阈值，而是
> 拿一整段 200 字场景描述去检索。本地也是同样的毛病（见 `docs/review.md` 的 R2）。

---

## 4. 节点逐个配

### 4.1 代码① 八方法评估

- 代码语言 **Python**
- 输入变量：`query`（String）= `开始 / sys.query`
- 可选输入：`prev_conditions`（String）= `会话变量 / conditions_json`（做多轮追问才需要，见 §6）
- 输出变量（**类型要选对**，否则 Dify 会报类型不匹配）：

| 变量 | 类型 | 用途 |
|---|---|---|
| `status` | String | `ok` / `need_more_info`，给条件分支用 |
| `assess_json` | String | 完整评估结果 → 代码② |
| `prompt_input` | String | 紧凑评估表 → LLM 节点 |
| `conditions_json` | String | 合并后的条件 → 写回会话变量 |
| `clarification_md` | String | 条件不全时的追问正文 → 直接回复 |

> ⚠️ **铁律：声明了几个输出，代码就必须只返回这几个键。**
> 多返回一个键（哪怕只是调试用）就会报 `Not all output parameters are validated.`，
> 整条链路直接红。三个代码节点都已按"键与声明完全一致"写好，不要再往 `return` 里加东西。

- 代码：整段粘贴 **`dify/code_node_assess_slim.py`**（约 49 KB / **512 行**，给 Dify 用）。
  `code_node_assess.py` 是带注释的可读版（62 KB / 1627 行），**不要直接粘**——
  Dify 代码框对超大粘贴会"粘了但没生效"，症状是 `Not all output parameters are validated.`。

  > **粘完怎么确认**：代码框里 Ctrl+F 搜 `BUILD`。
  > 文件最后一行是 `BUILD = "2026-11-17.2"` ——
  > 搜到了且值一致 = 粘全了且是新版；搜不到 = 被截断或还是旧版。
  > **不要用行号判断**（改动一次行数就漂，511→512 这种）。
  >
  > 改了可读版后跑 `python dify\build_slim.py` 重新生成，它会自动对拍 882 组确认语义不变。

### 4.2 条件分支

条件：`{{#assess.status#}}` **等于** `need_more_info`
- 满足 → 直接回复：`{{#assess.clarification_md#}}`
- 不满足 → 进知识检索

### 4.3 知识检索

- 查询变量：`{x}` → `开始 / sys.query`
- 知识库：勾选 §3 新建的那个
- 该节点上可以再覆盖一次 **Top K / Score 阈值**（两处设置，行为一致，建议保持一致）

### 4.4 代码③ 证据整理

- 输入：`result`（**Array[Object]**）= `知识检索 / result`
- 输出：`evidence_text`（String）、`evidence_json`（String）
- 代码：`dify/code_node_evidence.py`

### 4.5 LLM 方案决策

- 模型 `deepseek-v4-flash`，温度 **0**，最大 token 2000
- SYSTEM = `dify/prompts.md` §1
- USER = `dify/prompts.md` §2（两个变量：`assess.prompt_input`、`evidence.evidence_text`）

### 4.6 代码② 校验 + 兜底 + 渲染

- 输入：

| 变量 | 类型 | 来源 |
|---|---|---|
| `assess_json` | String | 代码① `assess_json` |
| `llm_json` | String | LLM `text` |
| `evidence` | Array[Object] | 知识检索 `result` |

- 输出：`answer_md`（String）、`mode`（String）、`violations`（String）
- 代码：`dify/code_node_finalize.py`

### 4.7 直接回复

```
{{#finalize.answer_md#}}
```

正文本身就是 Markdown（含表格），Dify 的回复框会正常渲染。

---

## 5. 发布

右上角 **发布更新** → 拿到访问链接。
之后再改任何配置，都要重新发布，否则"访问入口"跑的仍是旧版本
（你截图里"有未发布的更改 · 4 小时前"就是这个状态）。

---

## 6. 多轮追问（可选，但建议做，这是本地的一个卖点）

本地用"结构化条件合并"实现"埋深改成 60 m 呢？"。Dify 侧等价做法：

1. 右上「会话变量」新增 `conditions_json`（String，默认空）。
2. 代码① 的 `prev_conditions` 绑定 `{{#conversation.conditions_json#}}`。
3. 在代码① 之后加一个 **变量赋值** 节点：`conditions_json = {{#assess.conditions_json#}}`。
4. 用户点"新对话"时，会话变量自动重置。

代码① 里的 `merge_conditions()` 与本地的 `SiteConditions.merge` 逐字段相同
（对拍覆盖了 4 组追问），所以"埋深改成 60 m"→ 只覆盖埋深、其余条件保留，
评估整体重算，和本地表现一致。

---

## 7. 验收清单（做完逐条打勾）

| # | 检查 | 期望 |
|---|---|---|
| 1 | 知识库文档数 | 13（12 章 + course_handouts） |
| 2 | 索引完成后分块数 | ≈ 1337 |
| 3 | 场景 1（厚黏土污染羽）主方法 | 直流电阻率 DC，电极距 1.5 m、排列长 70.5 m（48 道） |
| 4 | 场景 2（城市找管线）主方法 | 探地雷达 GPR，250 MHz、时窗 74 ns |
| 5 | 场景 3（软土液化）主方法 | 面波 MASW，道间距 2.5 m、排列长 57.5 m |
| 6 | 场景 4（灰岩溶洞）主方法 | 直流电阻率 DC；总测线 1.02 km、680 点、成本 30.6（中） |
| 7 | 输入"我想做个物探" | 走追问分支，列出 3 个问题，不调模型 |
| 8 | 故意把温度调高/提示词改坏 | 出现"改用规则方案"的降级提示，数字不变 |
| 9 | 与本地同场景并排截图 | 主方法、采集参数、外业工作量三项完全一致 |

第 9 条就是汇报里"两种呈现"最硬的那张图。

---

## 8. 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 代码节点报 `main() got an unexpected keyword` | 节点输入变量名和函数参数名不一致 | 严格用 `query` / `prev_conditions` / `assess_json` / `llm_json` / `evidence` / `result` |
| 知识检索返回空数组 | Score 阈值太高 | 关掉阈值 |
| 正文里出现了模型编的数字 | 误把 LLM 输出直接当回复 | 回复必须绑 `finalize.answer_md`，不要绑 `llm.text` |
| 代码节点超时 | 单节点里做了多次网络调用 | 我们的节点纯计算，毫秒级；超时一般是把 HTTP 写进去了 |
| 改了配置但对话没变 | 没发布 | 点「发布更新」 |
| 中文提问召回差 | 用了旧的 12 文档知识库（没有中文条目） | 用 `dify/knowledge/` 重建 |
