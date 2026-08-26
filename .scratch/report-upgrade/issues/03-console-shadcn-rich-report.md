# 03 — 控制台 shadcn/ui 接入 + 富报告视图

**What to build:** 控制台接入 shadcn/ui（Card/Badge/Button/Progress/Input/Textarea/Checkbox/Switch），替换手写控件；报告区改为用结构化 summary 自绘富视图：Agent 卡片、ECharts（npm echarts）情绪环形与渠道声量条形、风险/机会/建议彩色组件、热门帖子榜；Markdown 下载链接保留。

**Blocked by:** 01 — 演示数据源与 Agent 结构化产出增肥

**Status:** ready-for-agent

- [ ] shadcn/ui 组件替换手写控件，tsc 构建零错误
- [ ] 报告区渲染新结构化字段与图表，信息密度对齐 HTML 下载件
- [ ] mock 链路走查：提交 → 进度 → 报告全链路无回归
