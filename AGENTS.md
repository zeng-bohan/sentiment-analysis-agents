# AGENTS.md

多智能体舆情分析系统（FastAPI / LangChain / SQLAlchemy / PostgreSQL / Redis / Docker），多智能体协作完成舆情采集、分析与报告生成，开源项目。

## Agent skills

### Issue tracker

工单以 markdown 文件存在 `.scratch/<feature>/` 下，规格在 `.scratch/<feature>/spec.md`，工单为 `issues/NN-<slug>.md`。See `docs/agents/issue-tracker.md`.

### Triage labels

五个标准角色标签：`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`。See `docs/agents/triage-labels.md`.

### Domain docs

Single-context：`CONTEXT.md` 在仓库根，ADR 在 `docs/adr/`。See `docs/agents/domain.md`.

## 协作约定

- **提交规范**：commit message 简短、专业，只描述技术变更本身；仓库内容（README、文档、commit、issue）仅限项目技术范畴，不得出现求职、招聘、简历等相关内容。
- **数据真实性**：README 与文档中所有性能指标、测试数字必须来自仓库内实际运行/测试的实测结果（如工具调用成功率、并发数、成本测算），禁止估算或编造。
- **讲解偏好**：写代码时同步讲解设计取舍，说明为什么这样设计。

## 本地演示与测试速查

- 重启演示：后端 `LLM_MOCK=true .venv/Scripts/python -m uvicorn app.main:app --port 8000`，前端 `cd frontend && npm run dev`（Vite proxy 转发 `/v1` 与 `/health`，后端零改动）。
- mock 语义：`LLM_MOCK=true` 保证无 key 可演示；接真实 key 后文字层走真模型，但工具层仍是固定 `_DEMO_POSTS` 演示数据、无真实爬虫——对外讲解**不得声称真实抓取**。
- 测试基线：pytest 全量 21 用例应全绿；SSE 流必须 `yield ServerSentEvent(...)`（裸字符串曾造成事件双前缀 bug）。
- 报告产物：`reports/task_*.html|md|pdf`（12 章富报告 + ECharts + reportlab PDF 实测 10 页）。
