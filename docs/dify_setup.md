# Dify Agent 对接方案

## 统一原则

- 本地 Python 与 Dify 共用同一份系统提示词：docs/dify_system_prompt.md。
- 共用同一份知识源：backend/data/knowledge/course_knowledge.json。修改后运行 export_dify_knowledge.py，生成 Dify 可上传的 Markdown。
- 共用方法定义、适用边界及同一参数表的知识描述；更新参数表或知识条目后应重新导出并在 Dify 更新文档。
- 两个运行环境的检索引擎不同，召回结果不保证逐条相同；模型和工具是否可调用也取决于 Dify 应用配置。

## 在 Dify 网站搭建

1. 在知识库中创建“工程物探课程与参考知识库”，上传 backend/data/knowledge/dify_knowledge.md。
2. 使用中文段落切分，先保留按标题分段；小规模知识库先用关键词/全文检索调试，确认查询能召回对应条目后再发布。
3. 打开 Agent 配置页，把 docs/dify_system_prompt.md 的正文复制到系统提示词区域。
4. 选择 Dify 已配置可用的模型，设置低随机性（如 temperature 0.2），保存并发布。
5. 用地下管线、灰岩溶洞、软土 Vs 结构等场景试跑，检查知识来源、是否调用参数工具、风险说明和追问行为。

## 与本地 Python 共享同一参数工具

Dify 云端 Agent 不能访问用户电脑上的 127.0.0.1。本地 API 目前只供本机网页使用。若要让 Dify 云端调用 Python 后端，需要将后端部署到可访问的 HTTPS 服务，并增加独立 API Token 鉴权，再在 Dify 添加自定义 OpenAPI 工具；不可把无鉴权本地服务直接暴露到公网，也不要把模型密钥写入 Dify 前端提示词。

在尚未部署 HTTPS 工具服务时，Dify 与本地项目可先共用系统提示词和导出的知识文档；参数判定逻辑应以本地 Python 工具为准，Dify 独立答复只作为第二个对照展示，不宣称两端共用同一次工具执行。

## 本地后端/网页启动

在 geophysics_agent_demo2 根目录分别开两个终端。

后端终端：

uv run --project backend uvicorn geophysics_agent.main:app --app-dir backend/src --reload

前端终端：

cd frontend
npm run dev

浏览器打开 http://localhost:5173。后端文档在 http://127.0.0.1:8000/docs。关闭各服务终端按 Ctrl+C。

首次运行若提示依赖缺失，先在项目根目录执行 uv sync --project backend；在 frontend 目录执行 npm install。
