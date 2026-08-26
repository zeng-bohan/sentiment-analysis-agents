import { useEffect, useState } from 'react'
import { getStats } from '../api/client'
import type { TaskStatus } from '../api/types'
import { Card, CardContent } from '@/components/ui/card'
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
    <Card size="sm" className="mb-4">
      <CardContent className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span>
          累计任务 <strong className="text-foreground">{stats.total}</strong>
        </span>
        {Object.entries(stats.by_status).map(([status, count]) => (
          <span key={status}>
            {STATUS_LABELS[status as TaskStatus] ?? status}{' '}
            <strong className="text-foreground">{count}</strong>
          </span>
        ))}
        <span>
          并发上限{' '}
          <strong className="text-foreground">{stats.concurrency_limit}</strong>
        </span>
      </CardContent>
    </Card>
  )
}
