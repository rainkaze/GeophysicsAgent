# 工程物探勘察方案推荐 Agent

课程结课汇报用的前后端分离原型：Vue 3 + TypeScript 前端、FastAPI + Pydantic 后端、OpenAI 兼容模型接口、本地课程知识检索和物探参数工具。

## 当前能力

- 支持自然语言描述勘察场景。
- 后端检索项目内课程知识条目，记录来源文件、页码和核对状态。
- LLM 可调用工程物探参数查询工具，查询结果会送回模型继续生成建议。
- 页面展示回答、检索依据、工具比较和执行状态。
- 模型配置只从项目根目录本机 `.env` 读取；密钥不进入浏览器。

知识条目尚需人工对照 PDF 逐条核验；标注“待人工核对”的内容不能作为最终课程引用。参数是教学演示经验数据，不能替代仪器参数、现场试验或专业判断。

## 配置

将 `.env.example` 复制为 `.env`，按模型服务商文档填写 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`。不要把 `.env` 提交至 GitHub。若服务商提供 OpenAI 兼容 Chat Completions 接口，填对应 API 根地址；本项目只将密钥交给后端 SDK。

## 启动后端

### PyCharm 启动（推荐）

先在 PyCharm 中为项目选择已有解释器：

`backend/.venv/Scripts/python.exe`

然后右键运行 `backend/run_api.py`。首次配置时，在 Run/Debug Configurations 中新增 Python 配置：

- Script path：项目路径下的 `backend/run_api.py`
- Working directory：项目根目录 `geophysics_agent_demo2`
- Python interpreter：`backend/.venv/Scripts/python.exe`

之后可以直接点击绿色运行按钮启动后端。该脚本内部会启动 Uvicorn，因此无需每次手动输入长命令。

### 命令行启动

在项目根目录执行：

```powershell
uv sync --project backend
uv run --project backend uvicorn geophysics_agent.main:app --app-dir backend/src --reload
```

后端地址 `http://127.0.0.1:8000`，健康检查 `/api/v1/health`，交互式接口文档 `/docs`。

## 启动前端

另开终端。PowerShell 如果提示禁止运行 `npm.ps1`，不要修改系统执行策略，改用 Windows 命令入口：

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

打开 `http://localhost:5173`。需要 Node.js/npm；关闭服务按 Ctrl+C。

## 检查

```powershell
cd frontend
npm run typecheck
npm run build
```

后端检查配置见 `backend/pyproject.toml`。依赖安装需要能访问 PyPI/npm registry；在使用 Clash 时可在当前终端临时设置 HTTP_PROXY/HTTPS_PROXY 指向本机代理端口，不必写入项目文件。

## 目录

- `backend/src/geophysics_agent/api`：HTTP 路由。
- `backend/src/geophysics_agent/agent`：LLM Agent 调度和提示词。
- `backend/src/geophysics_agent/knowledge`：本地课程知识检索。
- `backend/src/geophysics_agent/tools`：参数表与可调用工具。
- `backend/data/knowledge`：带出处元数据的知识条目。
- `backend/data/book`、`backend/data/PPT`：本地资料源，不要将受版权保护的整本书提交到公开仓库。
- `frontend/src`：Vue 页面、API 客户端与样式。
- `docs`：架构、知识库和课堂演示文档。
