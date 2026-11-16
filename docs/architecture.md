# 架构与数据流

浏览器 Vue 页面通过 `/api/v1/recommend` 提交自由文本。FastAPI 校验请求后，Agent 检索本地课程条目，将带来源的证据与用户输入交给兼容 OpenAI Chat Completions 的模型。模型可调用 `geophysical_param_lookup`；后端执行参数查表并将结果作为 tool message 返回模型。最终响应包含自然语言建议、课程证据、工具结果和运行事件。

信任边界：浏览器不接触模型 API Key；配置只由后端载入。知识命中不等同于已核验，响应需携带来源与核对状态。工具参数值是教学规则，不代表现场保证值。
