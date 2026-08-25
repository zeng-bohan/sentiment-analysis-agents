import { useEffect, useState } from 'react'
import { getStats } from '../api/client'
import type { TaskStatus } from '../api/types'
import { STATUS_LABELS } from './statusMeta'

interface Props {
  /** 变化时重新拉取统计（如任务终态后） */
  refreshKey: number
}

export function StatsHeader({ refreshKey }: Props) {
  const [stats, setStats] = useState<Awaited<ReturnType<typeof getStats>> | null>(
    null,
  )

  useEffect(() => {
    let cancelled = false
    getStats()
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
