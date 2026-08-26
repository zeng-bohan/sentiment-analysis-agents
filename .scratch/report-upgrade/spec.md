# Spec: 报告观感与深度升级（BettaFish 对标）

Status: ready-for-agent

## Problem Statement

当前报告（HTML/Markdown/PDF 与控制台报告区）把结构化结果直接 `str()` 进模板：Python 字典/列表裸奔、排版极简、内容每节一两行。对标 BettaFish 的章节制富报告（卡片、图表、数据密度），观感差距决定性地影响演示效果。

## Solution

三线并进：① 加厚演示数据源与 Agent 结构化产出（情绪占比、渠道声量、热门帖子）；② ReportEngine 章节制重做——HTML 模板（ECharts 图表、Agent 卡片、彩色标注块）+ 结构化 Markdown + reportlab PDF 升级（标题/表格 flowables）；③ 控制台接入 shadcn/ui 并用结构化 summary 自绘富报告视图。验收硬指标：**HTML 章节 ≥ 10、PDF ≥ 10 页（可程序化断言）**。

## User Stories

1. As a 演示者, I want 报告分 10+ 章节呈现（概览/背景/渠道/情绪/热点/三 Agent 深度/风险/机会/建议/附录明细）, so that 报告有专业分析报告的体量与结构。
2. As a 演示者, I want 情绪占比环形图、渠道声量条形图、互动指标磁贴, so that 数据一目了然。
3. As a 演示者, I want 每条风险/机会/建议以彩色标注块呈现, so that 结论可执行、可扫读。
4. As a 演示者, I want 附录含全部演示帖子的明细表（平台/内容/互动/情绪）, so that 报告的数据密度真实可信。
5. As a 演示者, I want PDF 至少 10 页且含标题与表格, so that 导出件可直接分发。
6. As a 演示者, I want 控制台报告区与 HTML 下载件信息密度一致, so that 现场演示与分发件不打折。
7. As a 开发者, I want Agent 结构化产出有明确的字段契约（见票①）, so that 模板与前端可并行开发。

## Implementation Decisions

- 图表：ECharts，HTML 报告经 CDN 引入；控制台用 npm echarts。PDF 走 reportlab 文本重排，不受影响。
- 组件库：shadcn/ui（Radix + Tailwind v4），拷贝式接入。
- 数据契约（票①产出、票②③消费，字段名即接口）：
  - `summary.overall_sentiment_breakdown = {positive, neutral, negative}`（0-100 数值）
  - `summary.total_posts_analyzed: int`
  - `agent_results.query.channel_stats = [{channel, posts, positive_pct, neutral_pct, negative_pct, engagement}]`
  - `agent_results.query.top_posts = [{platform, content, likes, comments, sentiment}]`
  - `agent_results.media.sentiment_breakdown = {positive, neutral, negative}`
  - `agent_results.media.channel_volume = [{channel, posts, engagement}]`
  - `agent_results.insight.priority_actions = [{action, rationale, urgency}]`
  - 现有字段（facts/analysis/advice/channels/sentiment/spread/risks/opportunities）语义不变。
- 演示数据源扩至 25-30 条帖子，覆盖微博/小红书/抖音/快手，带 likes/comments/sentiment。
- mock 文本保持确定性（无 key 可演示）；接入真实 API key 时文字由真实模型生成（现有能力，不属本票）。

## Testing Decisions

- Seam：后端 pytest 套件（现有）+ 新增断言（新字段存在、PDF 页数 ≥ 10、HTML 章节数 ≥ 10）。
- 前端仍按 ADR 0002 走 mock 链路人工走查；`tsc` 构建零错误。

## Out of Scope

- 真实爬虫接入、LLM 章节生成（BettaFish 式 IR 管线）、PDF 图表化、断点续传 SSE。

## Further Notes

- 缺陷修复 `.scratch/sse-prefix-fix/`（SSE 双前缀）挂起中，并入本特性票④收尾。
