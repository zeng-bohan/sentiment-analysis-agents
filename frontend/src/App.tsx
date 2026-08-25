import { useEffect, useState } from 'react'
import type { HealthResponse } from './api/types'

type HealthState =
  | { kind: 'loading' }
  | { kind: 'ok'; health: HealthResponse }
  | { kind: 'error'; message: string }

function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false
    fetch('/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<HealthResponse>
      })
      .then((health) => {
        if (!cancelled) setState({ kind: 'ok', health })
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setState({
            kind: 'error',
            message: err instanceof Error ? err.message : String(err),
          })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return state
}

function App() {
  const health = useHealth()

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold">舆情分析任务控制台</h1>
        {health.kind === 'loading' && (
          <span className="rounded-full bg-gray-200 px-3 py-1 text-xs text-gray-600">
            连接中…
          </span>
        )}
        {health.kind === 'ok' && (
          <span className="flex items-center gap-2 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
            <span className="size-2 rounded-full bg-green-500" />
            已连接 {health.health.app}
            {health.health.mock_llm && (
              <span className="rounded bg-amber-100 px-1.5 text-amber-700">
                Mock LLM
              </span>
            )}
          </span>
        )}
        {health.kind === 'error' && (
          <span className="flex items-center gap-2 rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">
            <span className="size-2 rounded-full bg-red-500" />
            后端未连接（{health.message}）
          </span>
        )}
      </header>

      {health.kind === 'error' && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          无法访问后端服务，请先启动后端（uvicorn app.main:app）后刷新页面。
        </div>
      )}

      <main>{/* 任务表单 / 事件时间线 / 结果区：后续票实现 */}</main>
    </div>
  )
}

export default App
