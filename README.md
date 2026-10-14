# 多智能体舆情分析

这是一个基于 FastAPI 的多智能体舆情分析演示系统。它通过 Query、Media、Insight 三类 Agent 协同处理任务，提供实时进度、任务取消和 HTML、Markdown、PDF 报告，并配有 React 分析控制台。

> 数据来源说明：当前工具层使用仓库内置的固定演示帖子，不会实时抓取微博、小红书、抖音或快手数据。分析结果用于演示工作流，不代表平台实时舆情。

## 功能

- 接收分析任务并由自定义调度器运行多个 Agent。
- 通过 SSE 推送任务进度，支持查询状态、取消任务和读取统计。
- 生成 HTML、Markdown 与 PDF 格式的报告。
- 提供 React 控制台，支持提交任务、查看执行进度和阅读报告。
- 没有配置模型 API Key 时自动使用 MockLLM；可选接入 OpenAI 兼容接口。

## 技术栈

| 范围 | 技术 |
| --- | --- |
| 后端 | Python、FastAPI、Pydantic Settings、LangChain Core |
| 前端 | React 19、TypeScript、Vite、Tailwind CSS、ECharts |
| 模型 | OpenAI 兼容 Chat API；无密钥时使用 MockLLM |
| 数据与任务状态 | Redis 缓存/任务快照；SQLAlchemy 与 Alembic 配置已提供 |
| 报告 | HTML、Markdown、PDF |
| 开发与 CI | Docker Compose、pytest、npm、Oxlint、GitHub Actions |

## 架构与目录

~~~text
app/
├── agents/       # Query、Media、Insight Agent
├── core/         # 模型、调度、缓存、任务与可观测性
├── report/       # 报告生成
├── tools/        # Agent 工具与演示数据源
├── main.py       # FastAPI 路由
└── schemas.py    # API 请求与响应模型
alembic/          # 数据库迁移
frontend/
├── src/          # React 控制台
└── package.json  # 前端命令和依赖
scripts/          # 评估与辅助脚本
templates/        # 报告模板
tests/            # 后端测试
docker-compose.yml
Dockerfile
.env.example
~~~

## 快速开始

### 本地开发

本地演示无需先启动数据库。未配置 `LLM_API_KEY` 时会使用 MockLLM；Redis 不可用时缓存和进度快照退化到内存。仓库含 Windows PowerShell 和类 Unix shell 两类常见命令。

~~~bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
~~~

在另一个终端启动前端：

~~~bash
cd frontend
npm ci
npm run dev
~~~

开发服务器默认位于 `http://localhost:5173`，并将 `/v1` 与 `/health` 转发到本地后端 `http://localhost:8000`。

### Docker Compose

Compose 会启动 API、PostgreSQL 和 Redis；API 容器启动时先执行 `alembic upgrade head`。复制 `.env.example` 为 `.env` 后，容器内数据库地址必须使用 Compose 服务名：

~~~dotenv
DATABASE_URL=postgresql+asyncpg://postgres:<密码>@postgres:5432/sentiment
REDIS_URL=redis://redis:6379/1
~~~

然后启动：

~~~bash
docker compose up --build -d
~~~

Compose 对宿主机开放 API `8000`、PostgreSQL `5433` 和 Redis `6380`。容器间连接使用服务名和容器端口。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 服务状态及当前是否使用 MockLLM |
| POST | `/v1/tasks` | 提交分析任务，JSON 至少包含 `query` |
| GET | `/v1/tasks/{task_id}` | 查询任务状态与结果摘要 |
| GET | `/v1/tasks/{task_id}/events` | SSE 进度流 |
| POST | `/v1/tasks/{task_id}/cancel` | 取消任务 |
| GET | `/v1/stats` | 当前任务统计 |
| GET | `/v1/reports/{task_id}?fmt=...`（`html`、`md` 或 `pdf`） | 下载报告 |

示例：

~~~bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"query":"分析新品近期口碑"}'
~~~

任务执行由当前 API 进程管理，任务状态主要保存在进程内并可写入 Redis 快照；这不是持久化任务队列。当前运行路径也未将 SQLAlchemy 模型接入任务读写。请求模型虽然声明了 `agents`、`parallel` 和 `title`，当前路由只把 `query` 交给任务管理器。API 未配置身份认证或权限控制，不应直接暴露到公网。

## 环境变量与数据库

配置项由 Pydantic Settings 从环境变量或仓库根目录 `.env` 读取，示例见 [.env.example](.env.example)。

| 变量 | 用途 |
| --- | --- |
| `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` | 连接 OpenAI 兼容模型；留空密钥时使用 MockLLM |
| `LLM_MOCK` | 显式启用 MockLLM |
| `REDIS_URL` | Redis 连接；失效时使用内存降级 |
| `DATABASE_URL`、`DATABASE_URL_MYSQL` | Alembic/SQLAlchemy 的数据库连接配置 |
| `TASK_CONCURRENCY`、`TASK_TIMEOUT_SECONDS` | 并发上限和任务超时 |
| `LANGSMITH_API_KEY` | 可选的 LangSmith 追踪 |

数据库模型和 Alembic 迁移已纳入仓库，Compose 会在 API 启动时执行迁移；当前 FastAPI 任务路径尚未使用这些 SQLAlchemy 模型作为任务持久化存储。单独检查迁移时，可将 `DATABASE_URL` 指向一个本地测试库，例如 SQLite：

~~~bash
export DATABASE_URL=sqlite+aiosqlite:///./migration-check.db
alembic upgrade head
alembic check
~~~

## 开发命令

后端：

~~~bash
pytest tests -q
~~~

前端：

~~~bash
cd frontend
npm ci
npm run dev
npm run build
npm run lint
~~~

CI 使用 Python 3.12 执行迁移检查和后端测试，并在前端安装依赖后运行构建。

## 许可证

[MIT](LICENSE)