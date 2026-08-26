# Spec: SSE 事件流双前缀修复

Status: ready-for-agent

## Problem Statement

`GET /v1/tasks/{id}/events` 的线上报文为 `data: data: {...}`：`sse_events` 生成器自行拼了 `data: ` 前缀，而 sse-starlette 的 `EventSourceResponse` 对生成器产出的每个字符串又会再加一层 `data: `。浏览器 EventSource 解析后 `event.data` 以 `data: ` 开头，`JSON.parse` 失败，事件永远无法被前端消费，连接陷入无限重连。既有测试未覆盖该缺陷：`_collect` 辅助函数直接订阅内部队列，绕过了线上格式化。

## Solution

`sse_events` 不再手工拼接 `data: ` 字符串，改为产出 sse-starlette 的 `ServerSentEvent` 对象：数据事件用 `ServerSentEvent(data=json.dumps(payload, ensure_ascii=False))`（线上格式 `data: {json}`），心跳用 `ServerSentEvent(comment="keep-alive")`（线上格式 `: keep-alive`）。终态后结束流的现有语义不变。

## User Stories

1. As a 前端开发者, I want SSE 报文中每个事件恰好带一层 `data: ` 前缀且内容为合法 JSON, so that EventSource 的 `event.data` 可直接 `JSON.parse`。
2. As a 前端开发者, I want 心跳以注释行（`: keep-alive`）下发, so that 连接保活且不污染事件数据。
3. As a 维护者, I want 线上格式有直接断言的测试, so that 序列化层回归能被测试套件捕获。

## Implementation Decisions

- 修复点仅限 `sse_events` 生成器的产出方式；订阅/快照/终态语义不变。
- 心跳从手工字符串（`":\n\n"`）改为 `ServerSentEvent(comment=...)`，保活职责仍留在生成器内。
- 前端 `parseEvent` 的容错剥离保留（对修复前后两种线上格式均兼容），不属本次后端改动范围。

## Testing Decisions

- Seam：`sse_events` 生成器的原始产出（线上格式层），新增直接断言测试——提交真实任务后迭代生成器，断言每个数据块为单层 `data: ` 前缀 + 可解析 JSON，且不存在 `data: data:`。
- 先写失败测试（红）再修复（绿）；修复后跑全量后端测试套件。
- 端到端：curl 实测线上报文 + 浏览器控制台走查确认事件恢复实时到达。

## Out of Scope

- 前端任何改动（`parseEvent` 容错保留）。
- SSE 协议层其他增强（事件命名、`id:`/`retry:` 字段、断点续传 Last-Event-ID）。

## Further Notes

- 该缺陷由任务控制台前端走查发现（见 `.scratch/task-console/issues/02-submit-sse-cancel.md` 的 Comments）；本修复解除 ADR 0001「后端零改动」约束的这一次例外——约束针对控制台集成需求，本票是独立的缺陷修复。
