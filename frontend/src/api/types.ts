/**
 * 与后端 Pydantic 模型一一对应的 API 契约类型。
 * 后端模型见 app/schemas.py；改动后端模型时同步更新此处。
 */

export type AgentName = 'query' | 'media' | 'insight'

export type TaskStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

/** POST /v1/tasks 请求体（AnalysisRequest） */
export interface AnalysisRequest {
  query: string
  agents?: AgentName[] | null
  parallel?: boolean
  title?: string | null
}

/** POST /v1/tasks 响应（TaskResponse，202） */
export interface TaskResponse {
  task_id: string
  status: TaskStatus
  progress: number
  stage: string
}

/** GET /v1/tasks/{id} 响应（TaskDetail） */
export interface TaskDetail {
  task_id: string
  status: TaskStatus
  progress: number
  stage: string
  error?: string | null
  summary?: Record<string, unknown> | null
  report_paths?: Record<string, string> | null
  total_tokens: number
  total_cost: number
}

/** GET /v1/stats 响应（StatsResponse） */
export interface StatsResponse {
  total: number
  by_status: Record<string, number>
  concurrency_limit: number
}

/** GET /health 响应 */
export interface HealthResponse {
  status: string
  app: string
  mock_llm: boolean
}

/** SSE data 载荷：进度事件与终态事件共用（见 task_manager.sse_events） */
export interface TaskEvent {
  status: TaskStatus
  progress?: number
  stage?: string
  error?: string
  summary?: Record<string, unknown> | null
  report_paths?: Record<string, string> | null
  total_tokens?: number
  total_cost?: number
}

export const TERMINAL_STATUSES: TaskStatus[] = [
  'succeeded',
  'failed',
  'cancelled',
]

export function isTerminal(status: TaskStatus): boolean {
  return TERMINAL_STATUSES.includes(status)
}
