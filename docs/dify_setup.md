# 可选：把课程知识库导出到 Dify

本项目的主链路是本地 Python Agent，**不依赖 Dify**。如果你还想用 Dify 做对照演示，
可以复用同一份知识库与同一套提示词。

## 导出一份可上传的 Markdown

```powershell
backend\.venv\Scripts\python.exe backend\scripts\export_dify_knowledge.py
```

生成 `backend/data/knowledge/dify_knowledge.md`，可直接上传到 Dify 知识库。

## 提示词在哪里

系统提示词已内置在代码里：`backend/src/geophysics_agent/agent/prompts.py` 的 `SYSTEM_PROMPT`。
修改提示词请改这个文件，不要再维护第二份 Markdown 副本。

## 需要注意的差异

- 本地 Agent 用 BM25 检索；Dify 用平台自带的检索策略，**召回结果不会条条相同**。
- 本地的六方法评估器（`analysis/calculator.py`）无法在 Dify 里运行，
  因此 Dify 端的回答**没有经过同样的确定性校验与规则兜底**，只能作为对照展示。
- 不要把本地无鉴权的 `127.0.0.1:8000` 直接暴露到公网，也不要把模型密钥写进 Dify 前端。
