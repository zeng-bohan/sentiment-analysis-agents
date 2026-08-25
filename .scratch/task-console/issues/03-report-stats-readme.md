# 03 — 报告展示 + 顶栏统计 + 演示物料

**What to build:** 任务成功终态后，结果区展示任务摘要、总 token 数与总费用；按 `fmt=md` 拉取报告正文以 Markdown 内嵌渲染，并提供 html/md/pdf 三种格式的下载直链；页面顶栏展示任务统计（总数、各状态分布、并发上限），任务状态变化后刷新；README 补充前端运行说明与演示 GIF/截图，使整个演示可按文档复现。最后对照规格全部用户故事在 mock 链路上完成一次完整走查。

**Blocked by:** 02 — 提交任务 + SSE 实时进度 + 取消

**Status:** ready-for-agent

- [ ] 成功终态展示 summary、total_tokens、total_cost
- [ ] Markdown 报告内嵌可读，html/md/pdf 三链接可下载
- [ ] 顶栏统计真实反映后端数据并随任务变化刷新
- [ ] README 含启动步骤（后端 mock 模式 + 前端 dev）与演示 GIF/截图
- [ ] 对照 spec 20 条用户故事完成完整走查并逐条核对
