import { useState } from 'react'
import { submitTask } from './api/client'
import type { AnalysisRequest } from './api/types'
import { StatsHeader } from './components/StatsHeader'
import { TaskForm } from './components/TaskForm'
import { TaskPanel } from './components/TaskPanel'
import { useHealth } from './useHealth'

function App() {
  const health = useHealth()
  const [taskId, setTaskId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [statsTick, setStatsTick] = useState(0)

  const handleSubmit = async (req: AnalysisRequest) => {
    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await submitTask(req)
      setTaskId(res.task_id)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

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
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          无法访问后端服务，请先启动后端（uvicorn app.main:app）后刷新页面。
        </div>
      )}

      <main className="space-y-4">
        {health.kind === 'ok' && <StatsHeader refreshKey={statsTick} />}

        <TaskForm submitting={submitting} onSubmit={handleSubmit} />

        {submitError && (
          <p className="rounded-md bg-red-50 p-3 text-sm text-red-600">
            提交失败：{submitError}
          </p>
        )}

        {taskId && (
          <TaskPanel
            key={taskId}
            taskId={taskId}
            onFinished={() => setStatsTick((t) => t + 1)}
          />
        )}
      </main>
    </div>
  )
}

export default App
