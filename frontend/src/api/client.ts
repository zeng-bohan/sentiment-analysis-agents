import type { AnalysisRequest, StatsResponse, TaskDetail, TaskResponse } from './types'

/** 从 FastAPI 错误响应中提取可读信息（detail 为字符串或 422 校验数组） */
async function readError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown }
    const detail = body.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d as { msg?: string }).msg ?? JSON.stringify(d))
        .join('；')
    }
    return JSON.stringify(body)
  } catch {
    return `HTTP ${res.status}`
  }
}

export async function submitTask(req: AnalysisRequest): Promise<TaskResponse> {
  const res = await fetch('/v1/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function getTask(taskId: string): Promise<TaskDetail> {
  const res = await fetch(`/v1/tasks/${taskId}`)
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function cancelTask(taskId: string): Promise<TaskDetail> {
  const res = await fetch(`/v1/tasks/${taskId}/cancel`, { method: 'POST' })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function getStats(): Promise<StatsResponse> {
  const res = await fetch('/v1/stats')
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}
