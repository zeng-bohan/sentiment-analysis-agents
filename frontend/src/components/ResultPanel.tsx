import { useEffect, useMemo, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ComposeOption, EChartsType } from 'echarts/core'
import type { BarSeriesOption, PieSeriesOption } from 'echarts/charts'
import type {
  GridComponentOption,
  LegendComponentOption,
  TooltipComponentOption,
} from 'echarts/components'
import type {
  SentimentBreakdown,
  TaskDetail,
  Urgency,
} from '../api/types'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ScrollArea } from '@/components/ui/scroll-area'

// 按需注册（控制包体）：环形图 + 条形图 + 必要组件
echarts.use([PieChart, BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

type EChartsOption = ComposeOption<
  | PieSeriesOption
  | BarSeriesOption
  | GridComponentOption
  | TooltipComponentOption
  | LegendComponentOption
>

interface Props {
  detail: TaskDetail
}

function reportUrl(taskId: string, fmt: 'html' | 'md' | 'pdf'): string {
  return `/v1/reports/${taskId}?fmt=${fmt}`
}

/* ----------------------------- 展示元数据 ----------------------------- */

const SENTIMENT_ORDER: (keyof SentimentBreakdown)[] = [
  'positive',
  'neutral',
  'negative',
]

const SENTIMENT_LABELS: Record<string, string> = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
}

const SENTIMENT_COLORS: Record<string, string> = {
  positive: '#22c55e', // green-500
  neutral: '#64748b', // slate-500
  negative: '#ef4444', // red-500
}

const SENTIMENT_BADGE_CLASSES: Record<string, string> = {
  positive: 'bg-green-100 text-green-700',
  neutral: 'bg-sky-100 text-sky-700',
  negative: 'bg-red-100 text-red-700',
}

function sentimentLabel(s: string): string {
  return SENTIMENT_LABELS[s] ?? s
}

/** 正/中/负彩色徽章（可带百分比） */
function SentimentBadge({ sentiment, pct }: { sentiment: string; pct?: number }) {
  return (
    <Badge className={SENTIMENT_BADGE_CLASSES[sentiment] ?? ''}>
      {sentimentLabel(sentiment)}
      {pct !== undefined ? ` ${pct}%` : ''}
    </Badge>
  )
}

const URGENCY_LABELS: Record<Urgency | string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

function UrgencyBadge({ urgency }: { urgency: string }) {
  if (urgency === 'high') {
    return <Badge variant="destructive">紧急度 高</Badge>
  }
  const cls =
    urgency === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-muted text-muted-foreground'
  return (
    <Badge className={cls}>紧急度 {URGENCY_LABELS[urgency] ?? urgency}</Badge>
  )
}

/* ----------------------------- ECharts 封装 ----------------------------- */

const CHART_HEIGHT = 240

/**
 * 图表容器固定高度；组件卸载时 dispose 实例，容器尺寸变化时自适应。
 */
function EChart({ option }: { option: EChartsOption }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<EChartsType | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const chart = echarts.init(el)
    chartRef.current = chart
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(el)
    return () => {
      observer.disconnect()
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    chartRef.current?.setOption(option, true)
  }, [option])

  return (
    <div
      ref={containerRef}
      style={{ height: CHART_HEIGHT }}
      className="w-full"
    />
  )
}

/* ----------------------------- 小部件 ----------------------------- */

/** 顶部统计磁贴 */
function StatTile({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Card size="sm" className="py-3">
      <CardContent className="space-y-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="text-lg font-semibold leading-tight">{children}</div>
      </CardContent>
    </Card>
  )
}

/** 风险（红）/机会（绿）标注块 */
function AnnotationBlock({
  kind,
  text,
}: {
  kind: 'risk' | 'opportunity'
  text: string
}) {
  const cls =
    kind === 'risk'
      ? 'border-red-400 bg-red-50 text-red-700'
      : 'border-green-400 bg-green-50 text-green-700'
  return (
    <div className={`rounded-md border-l-4 px-3 py-2 text-sm leading-5 ${cls}`}>
      {text}
    </div>
  )
}

/* ----------------------------- 主组件 ----------------------------- */

/** 成功终态的结果区：结构化富报告视图 + 三格式下载（缺结构化数据时回退 Markdown） */
export function ResultPanel({ detail }: Props) {
  const [markdown, setMarkdown] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const summary = detail.summary ?? null
  const overall = summary?.overall_sentiment_breakdown
  const totalPosts = summary?.total_posts_analyzed
  const queryResult = summary?.agent_results?.query
  const mediaResult = summary?.agent_results?.media
  const insightResult = summary?.agent_results?.insight

  const channelStats = queryResult?.channel_stats ?? []
  const topPosts = queryResult?.top_posts ?? []
  const mediaBreakdown = mediaResult?.sentiment_breakdown
  // 渠道声量优先用 media.channel_volume，缺失时从 query.channel_stats 推导
  const volumeData =
    mediaResult?.channel_volume && mediaResult.channel_volume.length > 0
      ? mediaResult.channel_volume
      : channelStats.map((c) => ({
          channel: c.channel,
          posts: c.posts,
          engagement: c.engagement,
        }))
  const risks = insightResult?.risks ?? []
  const opportunities = insightResult?.opportunities ?? []
  const advice = insightResult?.advice
  const priorityActions = insightResult?.priority_actions ?? []

  // 是否具备票①新契约的结构化字段：决定走富视图还是 Markdown 降级视图。
  // risks/opportunities 属旧字段（Markdown 视图同样包含），不作为富视图触发条件
  const hasStructured = Boolean(
    overall ||
      channelStats.length > 0 ||
      topPosts.length > 0 ||
      mediaBreakdown ||
      priorityActions.length > 0,
  )

  // 富视图不依赖 Markdown 文本；仅降级模式才拉取。
  // 本组件随单个任务挂载一次（TaskPanel 以 taskId 为 key），markdown/error 无需手动重置
  useEffect(() => {
    if (hasStructured) return
    let disposed = false
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
  }, [detail.task_id, hasStructured])

  const pieOption = useMemo<EChartsOption | null>(() => {
    if (!overall) return null
    const data = SENTIMENT_ORDER.map((key) => ({
      name: SENTIMENT_LABELS[key],
      value: Math.round(overall[key] * 100) / 100,
      itemStyle: { color: SENTIMENT_COLORS[key] },
    }))
    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}：{c}%（占比 {d}%）',
      },
      legend: {
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 12,
        textStyle: { fontSize: 11 },
      },
      series: [
        {
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
          label: { formatter: '{b} {c}%', fontSize: 11 },
          data,
        },
      ],
    }
  }, [overall])

  const barOption = useMemo<EChartsOption | null>(() => {
    if (volumeData.length === 0) return null
    return {
      tooltip: { trigger: 'axis' },
      legend: {
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 12,
        textStyle: { fontSize: 11 },
      },
      grid: { left: 8, right: 16, top: 16, bottom: 36, containLabel: true },
      xAxis: {
        type: 'category',
        data: volumeData.map((c) => c.channel),
        axisLabel: { fontSize: 11 },
      },
      yAxis: { type: 'value' },
      series: [
        {
          name: '帖子数',
          type: 'bar',
          data: volumeData.map((c) => c.posts),
          barMaxWidth: 20,
          itemStyle: { color: '#60a5fa', borderRadius: [3, 3, 0, 0] },
        },
        {
          name: '互动量',
          type: 'bar',
          data: volumeData.map((c) => c.engagement),
          barMaxWidth: 20,
          itemStyle: { color: '#f59e0b', borderRadius: [3, 3, 0, 0] },
        },
      ],
    }
  }, [volumeData])

  /* --------------------- 降级：无结构化数据 → Markdown 视图 --------------------- */

  if (!hasStructured) {
    return (
      <section className="space-y-3">
        <ReportHeader detail={detail} />
        <Alert>
          <AlertDescription>
            未获取到结构化分析数据，以下为 Markdown 报告内容。
          </AlertDescription>
        </Alert>
        {error && (
          <Alert variant="destructive" className="text-xs">
            <AlertDescription>报告加载失败：{error}</AlertDescription>
          </Alert>
        )}
        {!error && markdown === null && (
          <p className="text-xs text-muted-foreground">报告加载中…</p>
        )}
        {markdown !== null && (
          <ScrollArea className="max-h-96 rounded-md bg-muted/50 p-3 text-sm leading-6">
            <div className="markdown">
              <Markdown>{markdown}</Markdown>
            </div>
          </ScrollArea>
        )}
      </section>
    )
  }

  /* ------------------------------ 富报告视图 ------------------------------ */

  return (
    <section className="space-y-3 pt-1">
      <ReportHeader detail={detail} />

      {/* 顶部磁贴 */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="总帖数">
          {totalPosts !== undefined ? totalPosts.toLocaleString() : '—'}
        </StatTile>
        <StatTile label="总 tokens">
          {detail.total_tokens.toLocaleString()}
        </StatTile>
        <StatTile label="成本">¥{detail.total_cost.toFixed(4)}</StatTile>
        <StatTile label="整体情绪占比">
          {overall ? (
            <span className="flex flex-wrap gap-x-2 gap-y-1">
              {SENTIMENT_ORDER.map((key) => (
                <SentimentBadge key={key} sentiment={key} pct={overall[key]} />
              ))}
            </span>
          ) : (
            '—'
          )}
        </StatTile>
      </div>

      {/* 图表行 */}
      {(pieOption || barOption) && (
        <div className="grid gap-3 md:grid-cols-2">
          {pieOption && (
            <Card size="sm">
              <CardHeader>
                <CardTitle>整体情绪占比</CardTitle>
                <CardDescription>全部帖子的情绪分布（%）</CardDescription>
              </CardHeader>
              <CardContent>
                <EChart option={pieOption} />
              </CardContent>
            </Card>
          )}
          {barOption && (
            <Card size="sm">
              <CardHeader>
                <CardTitle>渠道声量</CardTitle>
                <CardDescription>各渠道帖子数与互动量对比</CardDescription>
              </CardHeader>
              <CardContent>
                <EChart option={barOption} />
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Query 卡片 */}
      {(channelStats.length > 0 || topPosts.length > 0) && (
        <Card size="sm">
          <CardHeader>
            <CardTitle>Query · 信息采集</CardTitle>
            {queryResult?.facts && (
              <CardDescription>{queryResult.facts}</CardDescription>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {channelStats.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="py-1.5 pr-3 font-medium">渠道</th>
                      <th className="py-1.5 pr-3 font-medium">帖子数</th>
                      <th className="py-1.5 pr-3 font-medium text-green-600">
                        正面
                      </th>
                      <th className="py-1.5 pr-3 font-medium">中性</th>
                      <th className="py-1.5 pr-3 font-medium text-red-600">
                        负面
                      </th>
                      <th className="py-1.5 font-medium">互动量</th>
                    </tr>
                  </thead>
                  <tbody>
                    {channelStats.map((c) => (
                      <tr key={c.channel} className="border-b last:border-b-0">
                        <td className="py-1.5 pr-3 font-medium">{c.channel}</td>
                        <td className="py-1.5 pr-3">{c.posts}</td>
                        <td className="py-1.5 pr-3 text-green-600">
                          {c.positive_pct}%
                        </td>
                        <td className="py-1.5 pr-3">{c.neutral_pct}%</td>
                        <td className="py-1.5 pr-3 text-red-600">
                          {c.negative_pct}%
                        </td>
                        <td className="py-1.5">{c.engagement}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {topPosts.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground">
                  热门帖子榜（按互动量）
                </p>
                <ol className="space-y-2">
                  {topPosts.map((p, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 rounded-md border px-3 py-2"
                    >
                      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                        {i + 1}
                      </span>
                      <div className="min-w-0 flex-1 space-y-1">
                        <p className="line-clamp-2 text-sm leading-5">
                          {p.content}
                        </p>
                        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                          <Badge variant="outline">{p.platform}</Badge>
                          <span>赞 {p.likes.toLocaleString()}</span>
                          <span>评 {p.comments.toLocaleString()}</span>
                        </p>
                      </div>
                      <SentimentBadge sentiment={p.sentiment} />
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Insight 卡片 */}
      {(risks.length > 0 ||
        opportunities.length > 0 ||
        advice ||
        priorityActions.length > 0) && (
        <Card size="sm">
          <CardHeader>
            <CardTitle>Insight · 洞察总结</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {risks.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  风险点
                </p>
                {risks.map((r, i) => (
                  <AnnotationBlock key={i} kind="risk" text={r} />
                ))}
              </div>
            )}
            {opportunities.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  机会点
                </p>
                {opportunities.map((o, i) => (
                  <AnnotationBlock key={i} kind="opportunity" text={o} />
                ))}
              </div>
            )}
            {advice && (
              <div className="rounded-md bg-muted/50 px-3 py-2 text-sm leading-5">
                {advice}
              </div>
            )}
            {priorityActions.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  优先行动清单
                </p>
                <ol className="space-y-2">
                  {priorityActions.map((a, i) => (
                    <li
                      key={i}
                      className="flex items-start justify-between gap-3 rounded-md border px-3 py-2"
                    >
                      <div className="min-w-0 space-y-0.5">
                        <p className="text-sm font-medium">{a.action}</p>
                        <p className="text-xs text-muted-foreground">
                          {a.rationale}
                        </p>
                      </div>
                      <UrgencyBadge urgency={a.urgency} />
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Media 卡片 */}
      {(mediaBreakdown || mediaResult?.spread || mediaResult?.analysis) && (
        <Card size="sm">
          <CardHeader>
            <CardTitle>Media · 媒体分析</CardTitle>
            {mediaResult?.sentiment && (
              <CardDescription className="flex items-center gap-2">
                整体情绪判定：
                <SentimentBadge sentiment={mediaResult.sentiment} />
              </CardDescription>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {mediaBreakdown && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  情绪分布
                </p>
                <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
                  {SENTIMENT_ORDER.map((key) => (
                    <div
                      key={key}
                      style={{
                        width: `${mediaBreakdown[key]}%`,
                        backgroundColor: SENTIMENT_COLORS[key],
                      }}
                    />
                  ))}
                </div>
                <p className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  {SENTIMENT_ORDER.map((key) => (
                    <span key={key} className="flex items-center gap-1">
                      <span
                        className="size-2 rounded-full"
                        style={{ backgroundColor: SENTIMENT_COLORS[key] }}
                      />
                      {SENTIMENT_LABELS[key]} {mediaBreakdown[key]}%
                    </span>
                  ))}
                </p>
              </div>
            )}
            {mediaResult?.spread && (
              <div className="flex flex-wrap gap-3">
                <div className="flex-1 basis-32 rounded-md border px-3 py-2">
                  <p className="text-xs text-muted-foreground">总互动（赞）</p>
                  <p className="text-base font-semibold">
                    {(mediaResult.spread.total_likes ?? 0).toLocaleString()}
                  </p>
                </div>
                <div className="flex-1 basis-32 rounded-md border px-3 py-2">
                  <p className="text-xs text-muted-foreground">高热帖子</p>
                  <p className="text-base font-semibold">
                    {(mediaResult.spread.hot_posts ?? 0).toLocaleString()}
                  </p>
                </div>
              </div>
            )}
            {mediaResult?.analysis && (
              <p className="rounded-md bg-muted/50 px-3 py-2 text-sm leading-5">
                {mediaResult.analysis}
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </section>
  )
}

/** 报告区头部：标题 + tokens/成本徽章 + 三格式下载链接（文案与旧版一致） */
function ReportHeader({ detail }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <h2 className="text-sm font-semibold">分析报告</h2>
      <Badge variant="secondary">
        tokens {detail.total_tokens.toLocaleString()}
      </Badge>
      <Badge variant="secondary">成本 ¥{detail.total_cost.toFixed(4)}</Badge>
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
  )
}
