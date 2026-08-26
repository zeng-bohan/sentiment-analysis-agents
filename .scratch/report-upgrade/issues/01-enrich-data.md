# 01 — 演示数据源与 Agent 结构化产出增肥

**What to build:** 演示者提交任务后，任务详情的 summary 里有"够写十页报告"的结构化数据：25-30 条多平台帖子（含互动数与情绪标签）、整体与分渠道情绪占比、渠道声量、热门帖子榜、优先行动清单。现有字段语义不变，受影响的测试断言同步更新。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] _DEMO_POSTS 扩至 25-30 条，覆盖微博/小红书/抖音/快手，含 likes/comments/sentiment
- [ ] summary 新增 overall_sentiment_breakdown 与 total_posts_analyzed
- [ ] query 结果新增 channel_stats 与 top_posts（字段契约见 spec）
- [ ] media 结果新增 sentiment_breakdown 与 channel_volume
- [ ] insight 结果新增 priority_actions
- [ ] 新增测试断言新字段存在；全量 pytest 绿
