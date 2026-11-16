# 工程物探勘察方案推荐 Agent

《Introductory Engineering Geophysics（工程地球物理导论）》课程项目 Demo。

输入一段自然语言描述的场地条件，输出**可核对的工程物探勘察方案**：
六种方法（GPR / DC-ERT / 面波 / 磁法 / FDEM / DAS）的逐项比选、按物理关系反算的
采集参数、外业布置与工作量估算、风险与验证措施，以及完整的执行轨迹。

技术栈：Vue 3 + TypeScript + Vite 前端，FastAPI + Pydantic 后端，OpenAI 兼容模型接口。

## 它和"直接用大模型"的区别

| 环节 | 通用大模型 | 本 Agent |
|---|---|---|
| 数值来源 | 模型自己写 | 代码按公式反算，模型不得改动 |
| 方法比选 | 凭语感排序 | 6 方法 × 目标 × 介质 × 埋深 × 干扰的确定性评估 |
| 结构 | 一段散文 | 机读 `SurveyPlan` + 渲染正文，二者同源 |
| 自检 | 无 | 14 条规则校验，不通过则回灌修复 |
| 可复现 | 每次不同 | `temperature=0`，同一输入同一结果 |
| 故障 | 直接报错 | 模型不可用自动降级为规则方案 |
| 追问 | 上下文丢失 | 会话内条件合并（"埋深改成 60 m 呢？"） |

## 当前能力

- 自然语言场景 → 结构化条件抽取（目标、介质、埋深范围、地表、干扰、预算）
- 六种方法的深度可行性、垂向分辨率、相对成本、限制与适用性判定
- 采集参数反算：天线频率与时窗、电极距与排列长度、道间距、测网密度、光缆长度
- 外业布置与工作量：测线数、总测线长度、测点数、相对成本档
- 方案自检与修复：校验失败自动回灌模型，仍失败则回退规则方案
- 课程知识检索：BM25 + IDF + 字段加权，输出命中词与相关性等级
- 多轮追问：会话内条件合并
- 完整可观测：每步耗时、模型调用次数与 token 用量、执行轨迹

## 快速开始

### 1. 配置模型

复制 `.env.example` 为 `.env`，填写 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`。
`.env` 已被 `.gitignore` 忽略，密钥不会进入浏览器或版本库。
没有可用模型时也可以运行：系统会走规则方案（`mode=degraded`），用于课堂演示兜底。

### 2. 启动后端（PyCharm 推荐）

项目**只有一个** Python 环境：`backend/.venv`。

1. `Settings → Project → Python Interpreter → Add Interpreter → Add Local → Select existing`
2. 选择 `backend/.venv/Scripts/python.exe`
3. 新建运行配置（**用普通 Python 配置，不要用 PyCharm 的 uv 运行器**）：
   - Script path：`backend/run_api.py`
   - Working directory：项目根目录 `geophysics_agent_demo2`
   - Interpreter：上一步的 `backend/.venv/Scripts/python.exe`
4. 点绿色运行按钮。等价于 `backend/.venv/Scripts/python.exe backend/run_api.py`

可选环境变量：`APP_HOST`（默认 127.0.0.1）、`APP_PORT`（默认 8000）、
`APP_RELOAD=1`（热重载，调试断点会失效）。

命令行方式：

```powershell
uv sync --project backend --extra dev
uv run --project backend uvicorn geophysics_agent.main:app --app-dir backend/src --reload
```

后端地址 `http://127.0.0.1:8000`，健康检查 `/api/v1/health`，
交互式文档 `/docs`，演示场景 `/api/v1/scenarios`。

### 3. 启动前端

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

打开 `http://localhost:5173`。

## 检查

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m mypy src --ignore-missing-imports

cd ..\frontend
npm.cmd run typecheck
npm.cmd run build
```

## 目录

```
backend/
  src/geophysics_agent/
    api/         HTTP 路由与依赖注入
    agent/       编排层：抽取、检索、规划、校验、渲染、会话、轨迹
    analysis/    确定性计算层：方法数据、物理关系、评估器、外业设计
    knowledge/   知识库加载与 BM25 检索
    domain/      领域模型与 API 契约
    core/        配置
  data/
    knowledge/   带出处元数据的课程知识条目
    book/ PPT/   本地资料源（版权原因未纳入版本库）
  tests/         55 项测试，含离线 Fake 模型用例
frontend/
  src/api/       类型定义与 API 客户端
  src/components/ 方法比选、方案详情、证据列表、执行轨迹
  src/views/     主页面
docs/
  architecture.md   分层、数据流、设计决策
  agent-workflow.md 状态机、校验规则、降级路径
  knowledge-base.md 知识库维护
  demo-script.md    课堂演示脚本
```

## 文档

- [架构与数据流](docs/architecture.md)
- [Agent 工作流程](docs/agent-workflow.md)
- [知识库维护](docs/knowledge-base.md)
- [课堂演示脚本](docs/demo-script.md)

## 边界说明

知识条目尚需人工对照 PDF 逐条核验，标注"待人工核对"的内容不能作为最终课程引用。
参数是教学演示经验数据，不能替代仪器参数、现场试验或专业判断。
物探解释具有多解性，方案必须结合钻孔、原位测试与工程师复核。
