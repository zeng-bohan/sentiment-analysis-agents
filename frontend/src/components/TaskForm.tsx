import { useState } from 'react'
import type { AgentName, AnalysisRequest } from '../api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'

const AGENTS: { name: AgentName; label: string }[] = [
  { name: 'query', label: 'Query（信息采集）' },
  { name: 'media', label: 'Media（媒体分析）' },
  { name: 'insight', label: 'Insight（洞察总结）' },
]

const MAX_QUERY = 2000

interface Props {
  submitting: boolean
  onSubmit: (req: AnalysisRequest) => void
}

export function TaskForm({ submitting, onSubmit }: Props) {
  const [query, setQuery] = useState('')
  const [agents, setAgents] = useState<AgentName[]>([])
  const [parallel, setParallel] = useState(true)
  const [title, setTitle] = useState('')

  const trimmed = query.trim()
  const queryError =
    trimmed.length === 0
      ? null // 未输入时不报错，仅禁用提交
      : trimmed.length > MAX_QUERY
        ? `分析需求不超过 ${MAX_QUERY} 字`
        : null
  const canSubmit = trimmed.length > 0 && !queryError && !submitting

  const toggleAgent = (name: AgentName) =>
    setAgents((prev) =>
      prev.includes(name) ? prev.filter((a) => a !== name) : [...prev, name],
    )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    onSubmit({
      query: trimmed,
      agents: agents.length > 0 ? agents : null,
      parallel,
      title: title.trim() || null,
    })
  }

  return (
    <Card>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium">
              分析需求 *
            </label>
            <Textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              placeholder="例如：分析近一周新能源汽车品牌的社交媒体舆情"
            />
            <p
              className={`mt-1 text-xs ${
                queryError ? 'text-destructive' : 'text-muted-foreground'
              }`}
            >
              {queryError ?? `${trimmed.length}/${MAX_QUERY}`}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">参与 Agent</span>
              {AGENTS.map((a) => (
                <label
                  key={a.name}
                  className="flex cursor-pointer items-center gap-1.5 text-sm"
                >
                  <Checkbox
                    checked={agents.includes(a.name)}
                    onCheckedChange={() => toggleAgent(a.name)}
                  />
                  {a.label}
                </label>
              ))}
              <span className="text-xs text-muted-foreground">
                不选 = 全部
              </span>
            </div>

            <label className="flex cursor-pointer items-center gap-1.5 text-sm">
              <Switch
                checked={parallel}
                onCheckedChange={(v) => setParallel(v === true)}
              />
              并行调度
            </label>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">
              报告标题（可选）
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="留空自动生成"
            />
          </div>

          <Button type="submit" disabled={!canSubmit}>
            {submitting ? '提交中…' : '提交任务'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
