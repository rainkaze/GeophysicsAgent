# 项目提示词（粘贴到新对话开头，帮助 AI 快速接手）

你正在帮我维护/改进一个本地项目：**工程物探勘察方案推荐 Agent**（课程项目，根目录 `geophysics_agent_demo2`）。

## 一句话定位
输入自然语言场地描述 → 输出**可核对**的工程物探勘察方案（八方法比选 + 反算采集参数 + 外业工作量 + 风险验证 + 执行轨迹）。**确定性数值由代码算，模型只写理由。**

## 技术栈与结构
- 后端 FastAPI + Pydantic（`backend/src/geophysics_agent/`），前端 Vue3+TS（`frontend/`）。
- 分层：`api`（路由）/ `agent`（编排）/ `analysis`（确定性计算）/ `knowledge`（混合检索）/ `domain`（领域模型）/ `core`（配置）。
- 唯一 Python 环境 `backend/.venv`，入口 `backend/run_api.py`。

## 工作流（8 步，只有 plan 和 repair 调模型）
intake 规则抽取 → 会话合并 → retrieve 混合检索（BM25+向量+Rerank）→ assess 八方法评估 → plan 模型写理由 → verify 14 条校验+修复 → design 外业 → render 正文。

## 已定的关键决策（不要推翻）
1. **数值由代码算，模型不得改**：`analysis/`（tables/physics/calculator/design）是唯一事实来源，模型只在 plan 选角色+写理由。
2. **知识库=文件即知识**：`backend/data/knowledge/` 下加 `.md` 即被索引（`book/` 教材英文 12 章 + `course/` 中文 17 条）。检索是**混合检索**：配置了 `DASHSCOPE_API_KEY` 时走「BM25 + text-embedding-v4 向量 RRF 融合 → qwen3-rerank 重排」（对齐 Dify）；无 key / 接口失败自动回退 BM25（离线兜底）。加文件见 `backend/data/knowledge/README.md`。
3. **已删除 Dify 耦合**：没有 `/tools/assess`；本地与 Dify 各自独立。Dify 对齐材料在 `dify/`：三个自包含代码节点（`code_node_assess/finalize/evidence` + `_slim` 粘贴版）、`prompts.md`、`kb_export.py`、`parity_test.py`（882 组逐字段对拍）、`setup.md`（施工图）。迁移用「工作室/Chatflow」建工作流，不用 Agent。
4. **评估如实**：八方法（GPR/直流电阻率/面波/地震折射/磁法/FDEM/TEM/DAS）没有"首选/适用"时，如实输出"无合适主方法、建议扩展方法或钻探为主"，**不强行指定不合适的方法**（含提示词、fallback、verifier、renderer 四处联动）。
5. 会话是进程内存（TTL 120min、上限 200），非数据库，重启即清空。
6. **GPR 按分辨率选频**：小目标（管线/UXO）优先保分辨率（管线≥250 MHz），不按深度选低频（`analysis/physics.py` 的 `design_gpr` + `GPR_TARGET_RESOLUTION_M`）。

## 已知局限与改进方向（按优先级）
- ① intake 目标/介质种类窄、只支持单目标 → 扩充 `analysis/tables.py` 的 `TARGET_ALIASES`/`MEDIUM_ALIASES` 最划算。
- ③ 检索已升级为混合检索（BM25+向量+Rerank）；纯 BM25 兜底时中文→英文词面召回仍弱。
- ④ 方法集已扩到 8 种（GPR/DC/面波/折射/磁法/FDEM/TEM/DAS）；课程提及的反射、微动与教材的重力/放射性/测井仍未实现，作"未覆盖"口径说明。

## 质量门禁（必须全绿）
```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m mypy src --ignore-missing-imports
cd ..\frontend
npm.cmd run typecheck
```

## 交流约定
- 涉及代码改动前先读源码，不只看 README。
- 改完必跑门禁 + 补/改测试。
- 数值/物探知识以教材与课件为准，拿不准就标注"教学经验值/待核对"，不冒充工程结论。
