# Spec: 任务控制台（React 前端）

Status: ready-for-agent

## Problem Statement

系统的任务 API（提交、SSE 进度、取消、报告、统计）已经完整，但没有任何界面去消费它：演示和日常使用都只能靠 curl 或读事件原始报文。非工程视角的人无法直观看到"提交了一个分析任务、几个 Agent 在并行干活、报告生成了"这件事。

## Solution

一个仓库内的 React 单页任务控制台：提交分析任务（含 Agent 名单与调度开关），实时观看 SSE 进度时间线与进度条，可随时取消；任务终态后展示摘要、token/费用与内嵌 Markdown 报告，并提供三种格式的下载；顶栏展示任务统计。开发期经 Vite proxy 连接后端，后端零改动。

## User Stories

1. As a 演示者, I want 在表单里输入舆情分析需求并提交, so that 我能发起一个分析任务而不需要 curl。
2. As a 演示者, I want 表单校验 query 非空且不超过 2000 字, so that 无效请求在页面就被拦下。
3. As a 演示者, I want 多选参与 Agent（query/media/insight）, so that 我能演示按名单裁剪调度。
4. As a 演示者, I want 切换并行/串行调度开关, so that 我能对比两种调度模式。
5. As a 演示者, I want 可选填写报告标题, so that 生成的报告有可读名称。
6. As a 演示者, I want 提交后立即看到任务已受理（queued）与 task_id, so that 我确认任务进入了系统。
7. As a 演示者, I want 实时看到进度条百分比与当前阶段文字, so that 我知道任务推进到哪一步。
8. As a 演示者, I want 事件以时间线日志形式滚动展示（时间 + 状态 + 阶段）, so that 调度过程可观察。
9. As a 演示者, I want 状态徽章区分 queued/running/succeeded/failed/cancelled, so that 一眼识别任务状态。
10. As a 演示者, I want SSE 断线后自动重连并恢复当前进度快照, so that 网络抖动不破坏演示。
11. As a 演示者, I want 任务运行中可点击取消, so that 我能中止不需要的任务。
12. As a 演示者, I want 取消后界面进入 cancelled 终态且事件流关闭, so that 界面状态与后端一致。
13. As a 演示者, I want 失败任务展示后端返回的 error 信息, so that 我能定位原因。
14. As a 演示者, I want 成功后看到摘要、总 token 数与总费用, so that 成本可观察。
15. As a 演示者, I want 报告 Markdown 内嵌渲染在页面里, so that 无需下载即可阅读。
16. As a 演示者, I want html/md/pdf 三种格式的下载链接, so that 我能取走原始产物。
17. As a 演示者, I want 顶栏展示总任务数、各状态分布与并发上限, so that 系统负载一目了然。
18. As a 演示者, I want 后端未就绪（503）或网络错误时看到明确错误提示而非白屏, so that 演示事故可快速定位。
19. As a 演示者, I want 提交未知 Agent 名单时展示 422 的校验信息, so that 表单错误可理解。
20. As a 开发者, I want 接口类型与后端 Pydantic 模型一一对应（TS 类型）, so that 前后端契约显式可见。

## Implementation Decisions

- 技术栈：React + Vite + TypeScript（strict）+ Tailwind CSS v4；单页，无路由、无状态管理库，React hooks 足够（ADR 0001）。
- 前端位于仓库内独立目录，独立 package.json；后端代码零改动（含 CORS，由 Vite dev proxy 转发 `/v1` 与 `/health` 规避，ADR 0001）。
- API 契约类型（AnalysisRequest / TaskResponse / TaskDetail / StatsResponse）按后端 Pydantic 模型手工镜像为 TS 类型；SSE 载荷类型为 `{status, progress?, stage?, error?}`。
- SSE 用浏览器原生 EventSource：终态到达后主动关闭；断线重连依赖 EventSource 内建重试 + 服务端快照恢复；30 秒心跳注释行由后端负责，前端无需处理。
- 报告展示：终态后从任务详情渲染 summary/tokens/cost；报告正文按 `fmt=md` 拉取文本用 react-markdown 渲染；html/pdf 提供直链下载。
- UI 语言中文；视觉形态为「表单区 + 事件时间线（含进度条与状态徽章）+ 结果区 + 顶栏统计」单页。
- 每张票一个 commit，直接提交 master（ADR 0001）。

## Testing Decisions

- 唯一验收 seam：**后端以 mock_llm 模式运行时的真实 HTTP API**（最高 seam，零新增 seam，ADR 0002）。
- 每张票的完成定义：在该 seam 上人工走查本票用户故事通过（提交→进度→终态全链路）。
- 不编写前端组件/单元测试（ADR 0002）；后端既有测试套件继续守护 API 行为，后端不改动。

## Out of Scope

- 前端单元/组件测试、E2E 测试框架。
- 历史任务的持久化列表（无列表接口；控制台仅展示本次会话内创建的任务）。
- 认证、多语言、移动端适配打磨、报告 PDF 页内预览。
- 对后端的任何改动（接口、CORS、部署脚本）。

## Further Notes

- 本项目用途为面试现场演示，时间盒 2-3 小时；完成后在 README 附运行说明与演示 GIF/截图。
- 演示脚本建议：mock 模式启动后端 → 提交任务 → 讲解事件时间线 → 中途取消一次 → 再跑一个成功任务展示报告与成本。
