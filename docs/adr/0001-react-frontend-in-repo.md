# ADR 0001: 前端进仓库，Vite dev proxy 连后端

日期：2026-08-25
状态：已采纳

## 背景

任务控制台（React）需要访问 FastAPI 后端。备选：独立前端仓库、或在后端加 CORS 中间件。

## 决策

- 前端放在本仓库独立目录（`frontend/`，独立 package.json），与后端同仓同版本演进。
- 开发期通过 Vite dev server 的 proxy 把 `/v1` 与 `/health` 转发到后端端口，**后端零改动**（不加 CORS）。
- 技术栈：React + TypeScript（strict）+ Tailwind CSS v4；单页应用，不引入路由与状态管理库，React hooks 足够。

## 后果

- 单仓库克隆即可跑通全栈演示；代价是仓库同时含 Python 与 Node 两套工具链（可接受，演示项目）。
- 若未来前端独立成产品，再迁移出仓库，届时本 ADR 作废。
