import { useEffect, useRef, useState } from 'react'
import { cancelTask, getTask } from '../api/client'
import { isTerminal, type TaskDetail, type TaskEvent, type TaskStatus } from '../api/types'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ResultPanel } from './ResultPanel'
import { StatusBadge } from './StatusBadge'

interface TimelineEntry {
  time: string
  status: TaskStatus
  stage?: string
  progress?: number
}

interface Props {
  taskId: string
  /** 终态后通知父组件（用于刷新统计等） */
  onFinished?: () => void
}

function nowLabel(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

/**
 * 容错解析 SSE data：后端 sse_events 生成器自带 "data: " 前缀，
 * sse-starlette 又包一层，线上格式为 "data: data: {...}"（EventSource
 * 解析后 ev.data 以 "data: " 开头）。此处剥掉多余前缀；后端修复后
 * 直接 JSON.parse 也能走通。
 */
function parseEvent(raw: string): TaskEvent | null {
  const s = raw.startsWith('data: ') ? raw.slice(6) : raw
  try {
    return JSON.parse(s) as TaskEvent
  } catch {
    return null
  }
}

export function TaskPanel({ taskId, onFinished }: Props) {
  const [detail, setDetail] = useState<TaskDetail | null>(null)
  const [events, setEvents] = useState<TimelineEntry[]>([])
  const [reconnecting, setReconnecting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const finishedRef = useRef(false)

  useEffect(() => {
    setDetail(null)
    setEvents([])
    setActionError(null)
    setCancelling(false)
    setReconnecting(false)
    finishedRef.current = false
    let disposed = false

    const finish = () => {
      if (finishedRef.current) return
      finishedRef.current = true
      // 终态以服务端详情为准（含 summary / tokens / cost）
      getTask(taskId)
        .then((d) => {
          if (!disposed) setDetail(d)
        })
        .catch(() => {})
        .finally(() => {
          if (!disposed) onFinished?.()
        })
    }

    // 先拉一次快照（SSE 只推增量，重连场景也靠它兜底）
    getTask(taskId)
      .then((d) => {
        if (!disposed) setDetail(d)
      })
      .catch(() => {})

    const es = new EventSource(`/v1/tasks/${taskId}/events`)
    es.onopen = () => setReconnecting(false)
    es.onerror = () => {
      // 服务端主动关闭前浏览器若在重试，标记重连中；终态关闭不标记
      if (!finishedRef.current && es.readyState === EventSource.CONNECTING)
        setReconnecting(true)
    }
    es.onmessage = (ev) => {
      const payload = parseEvent(ev.data)
      if (!payload) return
      setEvents((prev) => [
        ...prev,
        {
          time: nowLabel(),
          status: payload.status,
          stage: payload.stage,
          progress: payload.progress,
        },
      ])
      setDetail((d) =>
        d
          ? {
              ...d,
              status: payload.status,
              progress: payload.progress ?? d.progress,
              stage: payload.stage ?? d.stage,
            }
          : d,
      )
      if (isTerminal(payload.status)) {
        es.close()
        finish()
      }
    }

    return () => {
      disposed = true
      es.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- taskId 变化即重建整个订阅
  }, [taskId])

  const status = detail?.status ?? 'queued'
  const progress = detail?.progress ?? 0
  const active = status === 'queued' || status === 'running'

  const handleCancel = async () => {
    setCancelling(true)
    setActionError(null)
    try {
      const d = await cancelTask(taskId)
      setDetail(d)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err))
    } finally {
      setCancelling(false)
    }
  }

  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold">任务</h2>
          <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
            {taskId}
          </code>
          <StatusBadge status={status} />
          {reconnecting && (
            <Badge className="bg-orange-100 text-orange-700">重连中…</Badge>
          )}
          {active && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleCancel}
              disabled={cancelling}
              className="ml-auto"
            >
              {cancelling ? '取消中…' : '取消任务'}
            </Button>
          )}
        </div>

        {actionError && (
          <Alert variant="destructive" className="text-xs">
            <AlertTitle>操作失败</AlertTitle>
            <AlertDescription>{actionError}</AlertDescription>
          </Alert>
        )}

        <div>
          <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
            <span>{detail?.stage || '等待调度…'}</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} aria-label={`任务进度 ${progress}%`} />
        </div>

        {status === 'failed' && detail?.error && (
          <Alert variant="destructive" className="text-xs">
            <AlertTitle>任务失败</AlertTitle>
            <AlertDescription>失败原因：{detail.error}</AlertDescription>
          </Alert>
        )}

        <ScrollArea className="max-h-64 rounded-md bg-muted/50 p-2 font-mono text-xs">
          {events.length === 0 && (
            <p className="text-muted-foreground">等待事件…</p>
          )}
          {events.map((e, i) => (
            <p key={i} className="text-foreground/80">
              <span className="text-muted-foreground">[{e.time}]</span>{' '}
              {e.status}
              {e.stage ? ` · ${e.stage}` : ''}
              {e.progress !== undefined ? ` · ${e.progress}%` : ''}
            </p>
          ))}
        </ScrollArea>

        {status === 'succeeded' && detail && <ResultPanel detail={detail} />}
      </CardContent>
    </Card>
  )
}
