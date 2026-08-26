/**
 * 与后端 Pydantic 模型一一对应的 API 契约类型。
 * 后端模型见 app/schemas.py；改动后端模型时同步更新此处。
 */

export type AgentName = 'query' | 'media' | 'insight'

/** 情绪三分类（与后端 _SENTIMENT_KEYS 一致） */
export type Sentiment = 'positive' | 'neutral' | 'negative'

/** 情绪占比（0-100 数值，三项之和为 100，见 tools._pct_shares） */
export interface SentimentBreakdown {
  positive: number
  neutral: number
  negative: number
}

/** 渠道统计行（agent_results.query.channel_stats[]） */
export interface ChannelStat {
  channel: string
  posts: number
  positive_pct: number
  neutral_pct: number
  negative_pct: number
  engagement: number
}

/** 热门帖子（agent_results.query.top_posts[]，按互动量降序） */
export interface TopPost {
  platform: string
  content: string
  likes: number
  comments: number
  sentiment: Sentiment | string
}

/** 渠道声量行（agent_results.media.channel_volume[]） */
export interface ChannelVolumeEntry {
  channel: string
  posts: number
  engagement: number
}

/** 行动项紧急度 */
export type Urgency = 'high' | 'medium' | 'low'

/** 优先行动清单项（agent_results.insight.priority_actions[]） */
export interface PriorityAction {
  action: string
  rationale: string
  urgency: Urgency | string
}

/** Query Agent 结构化产出 */
export interface QueryAgentResult {
  agent?: string
  channels?: string[]
  facts?: string
  channel_stats?: ChannelStat[]
  top_posts?: TopPost[]
}

/** Media Agent 结构化产出 */
export interface MediaAgentResult {
  agent?: string
  sentiment?: string
  spread?: { total_likes?: number; hot_posts?: number }
  analysis?: string
  sentiment_breakdown?: SentimentBreakdown
  channel_volume?: ChannelVolumeEntry[]
}

/** Insight Agent 结构化产出 */
export interface InsightAgentResult {
  agent?: string
  risks?: string[]
  opportunities?: string[]
  advice?: string
  priority_actions?: PriorityAction[]
}

/** 三类 Agent 的结构化产出集合 */
export interface AgentResults {
  query?: QueryAgentResult
  media?: MediaAgentResult
  insight?: InsightAgentResult
}

/** 任务执行日志行（summary.logs[]） */
export interface SummaryLog {
  agent: string
  level: string
  message: string
}

/** GET /v1/tasks/{id} 的 summary 字段（ForumEngine._aggregate + 各 Agent 摘要） */
export interface TaskSummary {
  task_id?: string
  query?: string
  /** 整体情绪占比（0-100，和为 100）；票① 新增契约字段 */
  overall_sentiment_breakdown?: SentimentBreakdown
  /** 分析帖子总数；票① 新增契约字段 */
  total_posts_analyzed?: number
  agent_results?: AgentResults
  failed_agents?: string[]
  success_rate?: number
  elapsed_seconds?: number
  total_tokens?: number
  logs?: SummaryLog[]
}

export type TaskStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

/** POST /v1/tasks 请求体（AnalysisRequest） */
export interface AnalysisRequest {
  query: string
  agents?: AgentName[] | null
  parallel?: boolean
  title?: string | null
}

/** POST /v1/tasks 响应（TaskResponse，202） */
export interface TaskResponse {
  task_id: string
  status: TaskStatus
  progress: number
  stage: string
}

/** GET /v1/tasks/{id} 响应（TaskDetail） */
export interface TaskDetail {
  task_id: string
  status: TaskStatus
  progress: number
  stage: string
  error?: string | null
  summary?: TaskSummary | null
  report_paths?: Record<string, string> | null
  total_tokens: number
  total_cost: number
}

/** GET /v1/stats 响应（StatsResponse） */
export interface StatsResponse {
  total: number
  by_status: Record<string, number>
  concurrency_limit: number
}

/** GET /health 响应 */
export interface HealthResponse {
  status: string
  app: string
  mock_llm: boolean
}

/** SSE data 载荷：进度事件与终态事件共用（见 task_manager.sse_events） */
export interface TaskEvent {
  status: TaskStatus
  progress?: number
  stage?: string
  error?: string
  summary?: TaskSummary | null
  report_paths?: Record<string, string> | null
  total_tokens?: number
  total_cost?: number
}

export const TERMINAL_STATUSES: TaskStatus[] = [
  'succeeded',
  'failed',
  'cancelled',
]

export function isTerminal(status: TaskStatus): boolean {
  return TERMINAL_STATUSES.includes(status)
}
