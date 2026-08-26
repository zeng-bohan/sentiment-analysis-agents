import type { TaskStatus } from '../api/types'
import { Badge } from '@/components/ui/badge'
import { STATUS_LABELS, STATUS_STYLES } from './statusMeta'

export function StatusBadge({ status }: { status: TaskStatus }) {
  return (
    <Badge className={STATUS_STYLES[status] ?? 'bg-muted text-muted-foreground'}>
      {STATUS_LABELS[status] ?? status}
    </Badge>
  )
}
