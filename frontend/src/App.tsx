import { useState } from 'react'
import { submitTask } from './api/client'
import type { AnalysisRequest } from './api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
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
          <Badge variant="secondary" className="h-auto py-1">
            连接中…
          </Badge>
        )}
        {health.kind === 'ok' && (
          <Badge className="h-auto gap-2 bg-green-100 py-1 text-green-700">
            <span className="size-2 rounded-full bg-green-500" />
            已连接 {health.health.app}
            {health.health.mock_llm && (
              <span className="rounded bg-amber-100 px-1.5 text-amber-700">
                Mock LLM
              </span>
            )}
          </Badge>
        )}
        {health.kind === 'error' && (
          <Badge className="h-auto gap-2 bg-red-100 py-1 text-red-700">
            <span className="size-2 rounded-full bg-red-500" />
            后端未连接（{health.message}）
          </Badge>
        )}
      </header>

      {health.kind === 'error' && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>
            无法访问后端服务，请先启动后端（uvicorn app.main:app）后刷新页面。
          </AlertDescription>
        </Alert>
      )}

      <main className="space-y-4">
        {health.kind === 'ok' && <StatsHeader refreshKey={statsTick} />}

        <TaskForm submitting={submitting} onSubmit={handleSubmit} />

        {submitError && (
          <Alert variant="destructive">
            <AlertDescription>提交失败：{submitError}</AlertDescription>
          </Alert>
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
