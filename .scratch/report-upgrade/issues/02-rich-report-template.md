# 02 — ReportEngine 章节制富模板（HTML/MD/PDF）

**What to build:** 报告生成从"字典 str()"改为结构化章节装配：HTML 模板（Jinja）呈现报告头 + 10 个以上章节（概览/舆情背景/渠道声量/情绪结构/热点帖子榜/三 Agent 深度分析/风险/机会/建议/附录数据明细），ECharts（CDN）渲染情绪环形图与渠道声量条形图，风险/机会/建议为彩色标注块；Markdown 按章节结构化生成；PDF 渲染升级为 reportlab 标题/表格 flowables。

**Blocked by:** 01 — 演示数据源与 Agent 结构化产出增肥

**Status:** ready-for-agent

- [ ] fmt=html 打开可见 10+ 章节与 ECharts 图表，无裸 Python repr
- [ ] fmt=md 为结构化章节文本（标题/表格/列表），无 HTML 标签残留
- [ ] fmt=pdf 页数 ≥ 10 且含标题与表格（新增程序化断言测试）
- [ ] 全量 pytest 绿
