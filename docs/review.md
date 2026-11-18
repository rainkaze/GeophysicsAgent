# 项目体检报告（2026-11-17）

对象：`geophysics_agent_demo2`（本地 Agent）+ Dify 上已配置的那个 Agent 应用。
方法：读全部源码与文档；跑测试与四道门禁；**实际调用**模型/embedding/rerank 接口；
用 882 组条件做判据矩阵回放；复算 `docs/report-script.md` 里的每一个数字；
把 Dify 截图里的每个参数与本地配置逐项对照。

一句话结论：**工程质量比一般课设高一档**（确定性计算、校验器、降级路径、66 个测试、
四道门禁全绿），但有三类"会被当场问住"的地方：判据里有两处自相矛盾、
Dify 侧的配置方向错了（应用类型 + 知识库分段 + 检索阈值）、以及全部改动还没进 git。

---

## 0. 体检时实际跑出来的东西

| 检查 | 结果 |
|---|---|
| `pytest -q` | **66 passed**（1.5 s） |
| `ruff check` / `ruff format --check` | All checks passed / 60 files already formatted |
| `mypy src` | Success: no issues found in 33 source files |
| `npm run typecheck` / `build` | 通过，163 kB gzip 59 kB |
| DeepSeek 接口 `/models` | HTTP 200，可用模型：`deepseek-flash`、`deepseek-v4-pro` |
| 本地 `LLM_MODEL=deepseek-flash` | ✅ 在列表里，能用 |
| Dify 里的 `deepseek-v4-flash` | ⚠️ **不在**上面这个列表里。若 Dify 走的是同一个 endpoint，可能报"模型不存在"——请在 Dify 里点一次测试确认，或统一成 `deepseek-flash` |
| DashScope embedding（text-embedding-v4） | ✅ 可用，1024 维 |
| DashScope rerank（qwen3-rerank） | ✅ 可用，但对长场景 top1 只有 0.55–0.66（见 R5） |
| 知识库片段 | 1337 个，最长 941 字符 |
| git 状态 | **47 项改动未提交**（30 改 / 5 删 / 12 新增），只有 3 个 commit |

---

## P0：会直接影响答辩的

### R1. 全部工作量都还没提交

`git status` 显示 47 项改动（30 个修改、5 个删除、12 个新增未跟踪），包括整个
`dify-alignment.md`、`report-script.md`、`semantic.py`、12 章教材知识库、
`build_book_knowledge.py`；已删除但未提交的 5 个：`course_knowledge.json`、
`dify_knowledge.md`、`export_dify_knowledge.py`、`docs/dify_setup.md`、`docs/demo-script.md`。

影响：这不是"代码问题"，是"证据问题"。老师看仓库只能看到 3 个 commit，
其中最近那个还停留在旧架构；万一硬盘/目录出问题，两周的重构直接没了。

改法：按功能分批提交，别一次性 `git add -A`。建议顺序见本文末「提交计划」。

---

### R2. 判据与自己的注释打架：钢筋 vs GPR

`analysis/calculator.py` 模块注释：

> 其中第 5 步的区分很关键：**钢筋网会真的毁掉 GPR 数据**，而地形起伏只是要求做地形改正。

但 `analysis/catalog.py`：

```python
SEVERE_INTERFERENCE = {
    Method.GPR: frozenset(),          # ← 空集
    ...
    Method.MAGNETIC: frozenset({REBAR, FENCE, MACHINERY, POWERLINE}),
}
```

于是场景 2（"地表有钢筋混凝土地面…找管线"）输出：

```
gpr  max=4.8  margin=1.60  首选   ← 钢筋只进了 limitations，没有触发降级
```

同一份代码里，"注释说钢筋毁掉 GPR""判据说钢筋对 GPR 不严重"。老师只要读两处就会问。

改法（二选一，**别两件都做**）：

- **A（推荐，零副作用）**：把注释改成与判据一致——"钢筋网会显著压制 GPR 数据，
  需降低频率、避开钢筋走向并接受深度损失"。报告数字全部不变。
- **B（改判据）**：`SEVERE_INTERFERENCE[GPR]` 加入 `REBAR`。后果：场景 2 没有
  "首选"方法 → 改由余量最大的可用方法担任主方法，`docs/report-script.md` 的
  演示数字要重写，Dify 侧也要同步（跑一次 `parity_test.py` 就知道改哪）。

我只做了 A 之外的事：**没有动判据**，因为会连锁改文档和 Dify。

---

### R3. 分辨率从不参与判定（最容易被问住的一条）

`vertical_resolution_m` 算出来了，也显示在表里，但**没有任何判定用到它**。
后果（`docs/report-script.md` 里的那个例子，我复算过）：

```
输入：灰岩场地，目标埋深 20~30 m，找溶洞，有钢筋和高压线干扰
输出：面波为主（面波垂向分辨率 4.0 m）
```

"面波 4 m 的垂向分辨率"去承担"找 2~3 m 溶洞"的主方法——这在工程上站不住，
而且它恰好违背了项目自己写的"不强行指定不合适的方法"。

同源问题：`TARGET_DEPTH_FACTOR` 只修深度，不修分辨率；GPR 是唯一做了分辨率
约束的方法（`GPR_TARGET_RESOLUTION_M`），其它七种都没有。

改法：给每个目标一个典型尺度 `TARGET_SIZE_M`（管线 0.3 m、溶洞 2 m、UXO 0.3 m、
污染羽 5 m、含水层 3 m、液化层 2 m、分层 2 m），当
`vertical_resolution_m > TARGET_SIZE_M` 时把"首选/适用"降为"受限"，
并加一条 verifier（V015）提示"分辨率不足以分辨目标尺度"。

这会改变若干场景的主方法（岩溶 20~30 m 那个例子大概率从面波变直流电阻率），
属于**判据升级，需要你确认**再动手；动手时我会同步改 Dify 节点并重跑对拍。

---

### R4. Dify 侧的配置方向错了三处

详见 `dify/setup.md` §0，这里只列结论：

1. **应用类型是 Agent**，Agent 应用没有代码节点 → 八方法评估只能让模型"嘴上算"，
   两个呈现的数字必然对不上。你自己写的 `docs/dify-alignment.md` 也写着"用工作室/Chatflow"。
2. **知识库分段标识符 = `\n`**：你截图里的分块预览就是证据——`Chunk-4 · 7 characters`
   （只有 `[p.250]`）、`Chunk-3 · 39`。页码与正文被切成互不相干的两块，
   "可回引页码"在 Dify 侧直接失效。
3. **Score 阈值 = 0.7**：实测 qwen3-rerank 对 4 个演示场景的 top1 分数是
   0.55 / 0.62 / 0.65 / 0.66，**全部低于 0.7** → 检索结果会被清空，LLM 永远拿不到证据。

另外：知识库只上传了教材 12 章，**漏了 `course_handouts.md`（17 条中文条目）**；
"12 文档 / **0 个关联应用**"+"有未发布的更改"说明这次关联还停在草稿，没发布。

---

## P1：检索质量

### R5. BM25 没命中时，向量检索根本没跑

`knowledge/retriever.py`：

```python
scored = [...]                      # BM25 结果
if not scored:
    return RetrievalResult()        # ← 在这里就返回了
if self.semantic is not None and self.semantic.available:
    return self._semantic_search(...)
```

这正好废掉了 embedding 最该发挥作用的场景：**中文提问 + 英文教材**，词面本来就没有交集，
BM25 必然是 0，于是永远不会走向量召回。`test_unrelated_query_returns_nothing`
也只测了无 semantic 的情况，把这个 bug 固化了。

**已修**：无 BM25 命中时仍然尝试语义检索，失败再返回空。并补了两条测试。

### R6. 拿一整段场景描述去检索，top1 经常跑偏

实测（本地混合检索 top8）：

| 查询 | top1 | 分数 |
|---|---|---|
| 场景 4「山区路基找溶洞」 | `06_gravity#138` 6.12 **重力**测量应用 | 0.649 |
| 场景 1「厚黏土追踪污染羽」 | `EXT-EPA-MULTI-001` 通用"多证据约束" | 0.623 |
| 「溶洞探测用什么方法」 | `06_gravity#137` 重力测量应用 | 0.555 |

不是阈值的问题，是"200 字的场景描述"里噪声词太多（山区、路基、碎石、施工机械）。

改法（低成本、见效快）：检索时用**抽取出的关键实体拼短查询**——
`f"{target_cn} {medium_cn} 方法"`（如"溶洞 灰岩 方法"），或长/短两个查询各检索
一次再合并去重。我没动，因为会改变证据列表，需要你确认。

### R7. rerank 分数的量纲没标定

`RERANK_STRONG = 0.35 / RERANK_WEAK = 0.1` 是拍的。实测同一个 reranker 打出的分数
跨度很大（0.24 ~ 0.95），0.35 作"强相关"阈值基本恒真（4 个场景全部 quality=strong）。
建议把 `strong` 提到 0.6 左右，或在方案里说明"相关度分级是相对量"。

---

## P2：判据细节与工程卫生

| # | 问题 | 证据 | 建议 |
|---|---|---|---|
| R8 | GPR 点距 0.05 m → 场景 2 算出 **20400 个测点**，成本指数仍判"低" | `design_gpr` 的 `spacing=min(0.5,max(0.05,…))`；`build_design` 的成本只看测线长度 | 成本模型引入点距/测点数因子；或把 GPR 点距下限抬到 0.1 m |
| R9 | "受限"方法会作为**辅助方法**出现，且没有 mitigation | 场景 4：GPR（受限，1.07×）在 support 列表里 | `recommended_support` 排除 `CONSTRAINED`，或给辅助项也写 mitigation |
| R10 | `TARGET_DEPTH_FACTOR` 用 1.2 放大 FDEM/TEM 能力，注释却说"不允许 >1.2 放大" | `tables.py` 第 164 行注释 vs 第 205/225 行数据 | 改注释措辞（"最多 1.2×，且只用于尺寸大于探测量级的目标"） |
| R11 | `GPR-001` 条目正文讲的是"地震速度" | `course_handouts.md` 第 54 行 | **已修**：改名 `SEIS-VEL-001`，并同步改了 `prompts.py` 里的示例编号 |
| R12 | `httpx` 是运行时依赖却只在 `[dev]` 里 | `semantic.py` 顶层 `import httpx`；`pyproject.toml` 第 16 行 | **已修**：提到主依赖 |
| R13 | trace 文案写"BM25 检索课程知识"，实际是混合检索 | `runner.py` 第 99 行 | **已修** |
| R14 | `.env` 里两把 key 都能直接用（我实测通过），其中 DashScope 是 `sk-ws-` 开头的**临时令牌** | 实测 | 换长期 key；`docs` 加一句"演示前跑一次自检"；`.env` 已 gitignore，但别把整个目录压缩发出去 |
| R15 | `.embedding_cache.json` 30 MB，每次启动全量读入 | 文件大小 | 定期删除重建；或按文件分片缓存 |
| R16 | `LLM_PROVIDER` / `APP_ENV` 是死配置（`config.py` 有字段，无人读取） | 全仓库搜索只出现在定义处 | **已修**：两个字段与 `.env.example` 的对应行已删除 |
| R17 | `docs/report-script.md` 说"直流电阻率与 FDEM 辅助"，代码实际给 dc/refraction 作前两个辅助 | 我复算的 support 列表 | 讲稿按实际输出念，或改成"若干方法可作交叉验证" |
| R18 | 旧文档建议"Markdown 分段保留 `##` 层级"，措辞不准：教材 12 章用的是 **`###`** 三级标题，`##` 一个都没有 | 统计：h1=1、h2=0、h3=4~34 | **已改**：新文档改成"空行分段 + 页码内联"。实测 `###` 会被正确当作片段标题（如"8.2.10 Applications of resistivity surveying"），这对检索是好事，但分块边界仍以空行为准 |

---

## 需要你拍板的三件事

1. **R2 选 A 还是 B**（改注释，还是真把钢筋算作 GPR 的严重干扰）。
2. **R3 是否加入"分辨率 vs 目标尺度"判据**。加，会改主方法，但能堵住最刁的追问；
   不加，就得在汇报里主动声明"分辨率只作参考，未参与取舍"。
3. **R6 是否改成短查询检索**（会改变证据列表，方案数值不变）。

三件都是"改了两端都要同步"的类型，所以我只给方案没动代码。

---

## 我这次代为修改的（都可以 `git diff` 看）

| 文件 | 改动 | 风险 |
|---|---|---|
| `knowledge/retriever.py` | BM25 无命中时仍尝试语义检索 | 低（只在原本返回空时生效） |
| `tests/test_retriever.py` | 补 2 条用例覆盖上述路径 | 无 |
| `backend/pyproject.toml` | `httpx` 提到运行时依赖 | 无 |
| `agent/runner.py` | trace 文案"BM25 检索"→"混合检索" | 无 |
| `data/knowledge/course/course_handouts.md` | `GPR-001` → `SEIS-VEL-001` | 无（id 未被他处硬编码） |
| `agent/prompts.py` | 示例编号 `GPR-001` → `ERT-001` | 无 |
| `dify/`（新增整个目录） | Dify 侧三个节点 + 提示词 + 知识库导出 + 对拍脚本 + 施工图 | 新增文件，不影响本地运行 |

---

## 建议的提交计划

```powershell
cd D:\QQDownload\研一上\工程地球物理概论\geophysics_agent_demo2

# 1) 先提交"已经能用"的本地重构（这是工作量的主体）
git add backend/src backend/tests backend/scripts backend/data/knowledge
git add frontend/src docs README.md AGENTS.md .env.example .gitignore
git commit -m "重构：八方法确定性评估 + 校验/降级 + 混合检索知识库"

# 2) 再提交 Dify 侧（两种呈现）
git add dify
git commit -m "新增 Dify 侧实现：代码节点、提示词、知识库导出、两端对拍"

# 3) 最后清理
git add -A
git commit -m "清理：删除旧的 Dify 导出脚本与过时演示稿"
```

提完之后 `git log --oneline` 应该能看到"本地实现 / Dify 实现 / 对拍"三段，
这本身就是工作量最直观的证据。
