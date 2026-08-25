# 01 — 前端骨架与链路打通

**What to build:** 从零建立任务控制台前端：Vite + React + TypeScript(strict) + Tailwind 的最小应用，开发服务器经 proxy 转发 `/v1` 与 `/health` 到后端（后端零改动）。页面调用后端健康接口，向用户展示「服务已连接 + 应用名 + mock_llm 是否开启」，证明前后端链路贯通。前后端之间的 TS 接口类型（任务提交、任务详情、统计、SSE 载荷）在本票定稿，后续票复用。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] 前端独立目录内 `npm run dev` 可启动，无类型错误
- [ ] 经 dev server 访问后端健康接口返回真实数据（proxy 生效，后端未改）
- [ ] 页面展示连接状态、应用名与 mock_llm 标记
- [ ] mock_llm 模式后端 + 前端同时运行，人工走查通过（ADR 0002 唯一 seam）
