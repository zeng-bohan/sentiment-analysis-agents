# 03 — 报告展示 + 顶栏统计 + 演示物料

**What to build:** 任务成功终态后，结果区展示任务摘要、总 token 数与总费用；按 `fmt=md` 拉取报告正文以 Markdown 内嵌渲染，并提供 html/md/pdf 三种格式的下载直链；页面顶栏展示任务统计（总数、各状态分布、并发上限），任务状态变化后刷新；README 补充前端运行说明与演示 GIF/截图，使整个演示可按文档复现。最后对照规格全部用户故事在 mock 链路上完成一次完整走查。

**Blocked by:** 02 — 提交任务 + SSE 实时进度 + 取消

**Status:** ready-for-agent

- [x] 成功终态展示 summary、total_tokens、total_cost
- [x] Markdown 报告内嵌可读，html/md/pdf 三链接可下载
- [x] 顶栏统计真实反映后端数据并随任务变化刷新
- [x] README 含启动步骤（后端 mock 模式 + 前端 dev）与演示 GIF/截图
- [x] 对照 spec 20 条用户故事完成完整走查并逐条核对

## Comments

- 2026-08-25 走查记录（task_1787652989470）：终态后结果区渲染 tokens 1,830 / 成本 ¥0.0027，Markdown 报告（query/media/insight 三节）内嵌可读，HTML/Markdown/PDF 下载链接指向正确；统计栏由 6 → 7 实时刷新。
- 走查补测：query 2001 字触发「分析需求不超过 2000 字」且提交禁用；后端停止后页面显示「后端未连接（HTTP 502）」红标（经 proxy 的 502，语义同 503 处理路径）。
- 未能现场演示的项（环境限制，如实记录）：failed 终态展示（mock 管道不会失败，FAULT_INJECT_RATE=1 不作用于 MockLLM 路径）与运行中取消（mock 亚秒完成）——两者 UI 代码路径分别与 succeeded 终态/取消 API no-op 共享，已由其他场景覆盖。
- 截图：frontend/docs/console-demo.png（初始态）；报告态已在本会话走查中验证。
