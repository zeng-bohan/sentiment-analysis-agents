import type { TaskStatus } from '../api/types'
import { STATUS_LABELS, STATUS_STYLES } from './statusMeta'

export function StatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-700'
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}
