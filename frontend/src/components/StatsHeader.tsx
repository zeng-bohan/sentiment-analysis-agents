import { useEffect, useState } from 'react'
import type { StatsResponse, TaskStatus } from '../api/types'

const STATUS_LABELS: Record<TaskStatus, string> = {
  queued: '排队',
  running: '运行',
  succeeded: '完成',
  failed: '失败',
  cancelled: '取消',
}

interface Props {
  /** 变化时重新拉取统计（如任务终态后） */
  refreshKey: number
}

export function StatsHeader({ refreshKey }: Props) {
  const [stats, setStats] = useState<StatsResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch('/v1/stats')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<StatsResponse>
      })
      .then((s) => {
        if (!cancelled) setStats(s)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  if (!stats) return null

  return (
    <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-gray-200 bg-white px-4 py-2 text-xs text-gray-600">
      <span>
        累计任务 <strong className="text-gray-900">{stats.total}</strong>
      </span>
      {Object.entries(stats.by_status).map(([status, count]) => (
        <span key={status}>
          {STATUS_LABELS[status as TaskStatus] ?? status}{' '}
          <strong className="text-gray-900">{count}</strong>
        </span>
      ))}
      <span>
        并发上限{' '}
        <strong className="text-gray-900">{stats.concurrency_limit}</strong>
      </span>
    </div>
  )
}
