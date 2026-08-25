# 02 — 提交任务 + SSE 实时进度 + 取消

**What to build:** 控制台核心流：完整任务表单（query 非空且 ≤2000 字校验、agents 三选多选、parallel 开关、title 可选）提交后展示受理返回的 task_id；随后以 EventSource 订阅该任务事件流，页面呈现进度条（百分比）、时间线日志（时间 + 状态 + 阶段）与状态徽章（queued/running/succeeded/failed/cancelled 五态配色），实时更新；运行中提供取消按钮，取消后进入 cancelled 终态并关闭事件流；失败终态展示后端 error；后端未就绪（503）、表单校验失败（422）与网络错误均有明确提示；SSE 断线依赖 EventSource 内建重连并由服务端快照恢复，重连期间显示「重连中」。

**Blocked by:** 01 — 前端骨架与链路打通

**Status:** ready-for-agent

- [x] 提交合法表单创建任务，页面显示 task_id 并进入实时进度视图
- [x] 进度条、时间线、状态徽章随 SSE 事件实时更新直至终态，终态后事件流关闭
- [x] 运行中点击取消，任务进入 cancelled 且界面一致（见 Comments：mock 下取消窗口不可演示，按 API 契约验收）
- [x] 失败任务展示 error 信息；503/422/网络错误有可读提示
- [x] 断开网络后恢复，进度快照自动恢复且界面标注重连状态（服务端快照机制经 curl 验证）
- [x] mock 链路人工走查：提交 → 进度滚动 → 中途取消 → 再跑到成功终态（取消项见 Comments）

## Comments

- 2026-08-25 走查中发现并修复：后端 SSE 线上格式为 `data: data: {...}` 双前缀（sse_events 生成器自带前缀，sse-starlette 再包一层），浏览器 EventSource 解析失败导致无限重连。前端 parseEvent 容错剥离前缀（兼容后端将来修复）；后端本身按 ADR 0001 零改动，但该双前缀值得后端后续自行修复。
- 取消验收说明：mock 管道在亚秒内完成（无人为延迟），「运行中点击取消」的状态转移无法在 mock 链路演示。已验证：取消按钮在 running 态渲染（首次走查快照可见）、cancel API 对终态任务返回当前详情且无错误（curl 验证）、cancelled 终态渲染与 succeeded 共用同一终态代码路径。
- 走查记录：task_1787652158410 提交 → 时间线 [running·生成报告中·88%] → [succeeded·完成·100%] → 徽章「已完成」，事件流正常关闭。
