# Agent 工作流程

本文说明一次请求在 agent 内部如何流转、每一步的输入输出是什么、失败如何处理。

## 1. 状态机

```
                    ┌──────────────────┐
用户输入 ──▶ intake │ 条件是否完整？    │
                    └────────┬─────────┘
                     否 │         │ 是
                        ▼         ▼
              ┌─────────────┐  ┌──────────┐
              │clarification│  │ retrieve │
              └─────────────┘  └────┬─────┘
                                    ▼
                              ┌──────────┐
                              │  assess  │（六种方法确定性评估）
                              └────┬─────┘
                                   ▼
                              ┌──────────┐   LLMError
                              │   plan   │──────────┐
                              └────┬─────┘          │
                                   ▼                │
                              ┌──────────┐  error   │
                              │  verify  │──────────┤
                              └────┬─────┘          │
                        无 error   │   有 error      │
                                   │     ▼          │
                                   │ ┌────────┐     │
                                   │ │ repair │◀─┐  │
                                   │ └───┬────┘  │  │
                                   │     └───────┘  │
                                   ▼                ▼
                              ┌──────────────────────┐
                              │ render → remember    │
                              └──────────────────────┘

最终 mode：
- agent        模型方案通过校验
- clarification 条件不全，先追问
- degraded     模型不可用 / 未通过校验，回退规则方案
```

## 2. 每一步的输入输出

| 步骤 | 输入 | 输出 | 失败处理 |
|---|---|---|---|
| intake | 用户原文、会话旧条件 | `SiteConditions` | 抽取失败只会导致追问 |
| retrieve | 用户原文 | `Evidence[]` + 相关性等级 | 知识库异常 → HTTP 503 |
| assess | 完整条件 | 六种方法 `MethodAssessment` + `FieldDesign` | 条件不全 → 抛 `ValueError`（上游已拦截） |
| plan | 条件、评估表、证据 | `PlanDraft`（JSON） | `LLMError` → 规则兜底 |
| verify | 草案、条件、评估表 | `Violation[]` | 规则异常不被吞掉，直接进 trace |
| repair | 草案 + 错误列表 | 新 `PlanDraft` | 调用失败 → 计数后兜底 |
| design | 最终主方法 | `FieldDesign` | 无主方法时返回空设计 |
| render | 方案、评估、证据 | Markdown 正文 | 纯函数，不失败 |

## 3. 校验规则清单

| 编号 | 级别 | 触发条件 |
|---|---|---|
| V001 | error / warning | 没有主方法（若有可行方法则 error，全不可行则 warning） |
| V002 | error | 主方法最大探测深度不足 |
| V003 | error | 主方法被判为"不适用" |
| V004 | error | 主方法深度余量 < 1.15× |
| V005 | error | 主方法"受限"但未给出 mitigation |
| V006 | warning | 主方法与评估器推荐不一致 |
| V007 | error | 把"首选"方法排除 |
| V008 | error | 出现多个主方法 |
| V009 | error | 场地干扰影响主方法但未给出 mitigation |
| V010 | warning | UXO 目标未用磁法/FDEM 作主方法 |
| V011 | error | DAS 作主方法但未说明光缆来源 |
| V012 | error | 验证措施缺少钻孔/试验剖面等可执行动作 |
| V013 | warning | 风险少于 3 条 |
| V014 | error | 用户预算偏低但方案为高成本档 |

`error` 触发修复循环；`warning` 只写入响应的 `warnings`，供前端提示。

## 4. 修复循环

```
draft  ──▶ verify ──▶ 有 error？
                        │否 → 通过
                        │是 → repair（≤ planner_max_repairs 次）
                                │
                                ├─ 仍不通过 → fallback_plan（degraded）
                                └─ 调用失败 → fallback_plan（degraded）
```

`fallback_plan` 不依赖模型，直接按评估器结论生成方案：
首选方法 → 主方法；适用/辅助 → 最多两个辅助；其余全部列为"不建议采用"，
并附上评估器给出的理由。因此**兜底方案必然物理自洽**，不需要再修。

## 5. 执行轨迹（trace）

每一步都会记录到响应的 `trace` 数组：

| step | 典型内容 |
|---|---|
| intake | 解析出的条件摘要 |
| clarify | 缺少几个关键字段 |
| retrieve | 命中条数、相关性等级、最高分 |
| assess | 设计埋深、推荐主方法 |
| plan | 草案条目数 / 模型不可用 |
| verify | error 与 warning 数量 |
| repair#N | 修复后剩余 error 数 |
| fallback | 回退原因 |
| design | 总测线长度、成本指数 |
| render | 正文字符数 |

前端把 trace 渲染成时间线，是"这个方案是怎么来的"最直接的证据。

## 6. 会话记忆

- 存储的是**结构化条件**，不是聊天记录；
- 追问时把新抽取结果 `merge` 进旧条件（只覆盖本次提到的字段）；
- 会话有 TTL（默认 120 分钟）与容量上限（默认 200 个）；
- `POST /recommend` 传 `reset: true` 可清空当前会话，对应前端"新对话"。

## 7. 降级路径（演示前建议实测）

| 路径 | 触发方式 | 预期表现 |
|---|---|---|
| 正常 | 配置可用 Key | `mode=agent`，trace 含 plan/verify |
| 信息不足 | 输入"我想做个物探" | `mode=clarification`，3 个追问 |
| 模型不可用 | `ENABLE_LLM=false` 或填错 Key | `mode=degraded`，正文顶部提示规则生成 |
| 方案不合格 | 模型给出深度不足的主方法 | trace 出现 `repair#1`；修复失败则 `fallback` |
