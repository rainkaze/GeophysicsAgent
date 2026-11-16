/** 后端 API 客户端：统一错误处理与类型标注。 */

import type { RecommendResponse, Scenario } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

/** 后端返回的错误体（FastAPI 的 detail 字段）。 */
interface ErrorBody {
  detail?: unknown
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new Error(`无法连接后端服务（${API_BASE}），请确认 FastAPI 已启动`)
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorBody | null
    const detail = body?.detail
    throw new Error(typeof detail === 'string' ? detail : `请求失败（HTTP ${response.status}）`)
  }

  return (await response.json()) as T
}

/** 获取内置演示场景。 */
export function fetchScenarios(): Promise<Scenario[]> {
  return request<Scenario[]>('/scenarios')
}

/** 提交场景描述，获取结构化勘察方案。 */
export function recommend(
  message: string,
  conversationId: string | null,
  reset = false,
): Promise<RecommendResponse> {
  return request<RecommendResponse>('/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId, reset }),
  })
}
