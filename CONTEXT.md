# CONTEXT

舆情分析多智能体系统的领域词汇表。后端为 FastAPI，异步任务架构；`frontend/` 为 React 任务控制台（见 ADR 0001）。

## 术语表

- **任务（Task）**：一次舆情分析执行，由 `POST /v1/tasks` 受理（202），生命周期为状态机 `queued → running → succeeded | failed | cancelled`。
- **Agent**：三类分析角色 `query / media / insight`，由 ForumEngine 并行调度；提交任务时可选择性指定参与名单。
- **事件流（SSE）**：`GET /v1/tasks/{id}/events` 服务端推送的进度事件，载荷为 `{status, progress, stage}`（失败时含 `error`），终态后流结束；30 秒心跳保活；断线重连后服务端自动恢复当前快照。
- **报告（Report）**：ReportEngine 产出的分析报告，`html / md / pdf` 三种格式，经 `GET /v1/reports/{id}?fmt=` 以文件形式下发。
- **任务控制台（Task Console）**：本次新增的 React 前端，消费上述任务 API，提供提交、实时进度、取消与报告展示。
- **Mock LLM**：`settings.use_mock_llm` 离线模式，不调真实模型，用于本地开发与前端验收（见 ADR 0002）。

## 关键约束

- 后端 API 是前后端之间唯一契约；前端不直连数据库或内部模块。
- 后端不为前端做任何改动（含 CORS，由 Vite dev proxy 规避，见 ADR 0001）。
