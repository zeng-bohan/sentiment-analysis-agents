import { useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import type { TaskDetail } from '../api/types'

interface Props {
  detail: TaskDetail
}

function reportUrl(taskId: string, fmt: 'html' | 'md' | 'pdf'): string {
  return `/v1/reports/${taskId}?fmt=${fmt}`
}

/** 成功终态的结果区：成本摘要 + 内嵌 Markdown 报告 + 三格式下载 */
export function ResultPanel({ detail }: Props) {
  const [markdown, setMarkdown] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let disposed = false
    setMarkdown(null)
    setError(null)
    fetch(reportUrl(detail.task_id, 'md'))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.text()
      })
      .then((text) => {
        if (!disposed) setMarkdown(text)
      })
      .catch((err: unknown) => {
        if (!disposed)
          setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      disposed = true
    }
  }, [detail.task_id])

  return (
    <section className="space-y-3 rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold">分析报告</h2>
        <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          tokens {detail.total_tokens.toLocaleString()}
        </span>
        <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          成本 ¥{detail.total_cost.toFixed(4)}
        </span>
        <span className="ml-auto flex items-center gap-2 text-xs text-blue-600">
          下载：
          <a href={reportUrl(detail.task_id, 'html')} className="hover:underline">
            HTML
          </a>
          <a href={reportUrl(detail.task_id, 'md')} className="hover:underline">
            Markdown
          </a>
          <a href={reportUrl(detail.task_id, 'pdf')} className="hover:underline">
            PDF
          </a>
        </span>
      </div>

      {error && (
        <p className="rounded-md bg-red-50 p-2 text-xs text-red-600">
          报告加载失败：{error}
        </p>
      )}
      {!error && markdown === null && (
        <p className="text-xs text-gray-400">报告加载中…</p>
      )}
      {markdown !== null && (
        <div className="markdown max-h-96 overflow-y-auto rounded-md bg-gray-50 p-3 text-sm leading-6">
          <Markdown>{markdown}</Markdown>
        </div>
      )}
    </section>
  )
}
