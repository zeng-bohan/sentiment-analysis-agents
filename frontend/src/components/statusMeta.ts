import type { TaskStatus } from '../api/types'

/** 任务状态的中文标签与徽章配色，全站共享（StatusBadge / StatsHeader） */
export const STATUS_LABELS: Record<TaskStatus, string> = {
  queued: '排队中',
  running: '运行中',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

export const STATUS_STYLES: Record<TaskStatus, string> = {
  queued: 'bg-gray-100 text-gray-700',
  running: 'bg-blue-100 text-blue-700',
  succeeded: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-amber-100 text-amber-700',
}
