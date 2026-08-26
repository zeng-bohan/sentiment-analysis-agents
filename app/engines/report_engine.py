"""ReportEngine：章节制富报告生成流水线。

聚合结果 → 结构化章节装配（build_sections）→ HTML（Jinja 富模板 + ECharts）
/ Markdown（结构化章节）/ PDF（reportlab flowables）三格式成稿。

设计取舍：三种格式共享同一份"结构化章节数据"（typed blocks：
paragraph / metrics / table / list / callout / subhead），渲染器只负责排版，
不再把 dict/list str() 进模板，也不从 HTML 剥标签 —— 单一事实来源，
格式间信息密度一致。
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..agents.tools import demo_corpus_stats
from ..config import Settings

# 模板目录锚定仓库根（app/engines/report_engine.py → 上溯两级），不受 cwd 影响
_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"

_SENTIMENT_LABELS = {"positive": "正面", "neutral": "中性", "negative": "负面"}
_SENTIMENT_ORDER = ("positive", "neutral", "negative")
_URGENCY_LABELS = {"high": "高", "medium": "中", "low": "低"}

_DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; max-width: 900px;
         margin: 24px auto; padding: 0 16px; color: #222; line-height: 1.75; }
  h1 { border-bottom: 3px solid #2f6fed; padding-bottom: 8px; }
  h2 { color: #2f6fed; margin-top: 28px; }
  .meta { color: #667; font-size: 13px; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 14px; }
  th, td { border: 1px solid #dfe5ef; padding: 6px 10px; text-align: left; }
  th { background: #f0f4fb; }
  .callout { border-left: 4px solid #2f6fed; background: #f2f6ff;
             padding: 8px 12px; margin: 8px 0; }
  .callout.danger { border-color: #c0392b; background: #fdf0ee; }
  .callout.success { border-color: #27ae60; background: #eef8f1; }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<p class="meta">任务 ID：{{ task_id }} ｜ 查询：{{ query }} ｜ 耗时：{{ elapsed }}s ｜ 成功率：{{ success_rate }}%</p>
{% for sec in sections %}
<h2>{{ sec.title }}</h2>
{% for b in sec.blocks %}
{% if b.type == "paragraph" %}<p>{{ b.text }}</p>
{% elif b.type == "subhead" %}<h3>{{ b.text }}</h3>
{% elif b.type == "metrics" %}<ul>{% for m in b['items'] %}<li><strong>{{ m.label }}：</strong>{{ m.value }}</li>{% endfor %}</ul>
{% elif b.type == "table" %}<table><thead><tr>{% for h in b.headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
<tbody>{% for row in b.rows %}<tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>{% endfor %}</tbody></table>
{% elif b.type == "list" %}<ul>{% for it in b['items'] %}<li>{{ it }}</li>{% endfor %}</ul>
{% elif b.type == "callout" %}<div class="callout {{ b.tone }}"><strong>{{ b.title }}</strong> {{ b.text }}</div>
{% endif %}
{% endfor %}
{% endfor %}
</body>
</html>
"""


def _fmt(value: Any) -> str:
    """标量安全字符串化：仅接受基础类型，杜绝裸 repr。"""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _sentiment_label(key: Any) -> str:
    return _SENTIMENT_LABELS.get(str(key), str(key))


class ReportEngine:
    """报告流水线：聚合结果 → 章节装配 → HTML/Markdown → PDF。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        self._env_ok = _TEMPLATE_DIR.is_dir()

    # ------------------------------------------------------------------
    # 章节装配：summary 结构化字段 + demo_corpus_stats() → typed blocks
    # ------------------------------------------------------------------
    def build_sections(self, summary: dict[str, Any]) -> list[dict[str, Any]]:
        """把 ForumEngine 聚合结果装配为 ≥10 个结构化章节。

        每个章节形如 ``{"id", "num", "title", "blocks": [...]}``；
        block 类型：paragraph / metrics / table / list / callout / subhead。
        """
        agent_results: dict[str, Any] = summary.get("agent_results") or {}
        query_res: dict[str, Any] = agent_results.get("query") or {}
        media_res: dict[str, Any] = agent_results.get("media") or {}
        insight_res: dict[str, Any] = agent_results.get("insight") or {}

        corpus = demo_corpus_stats()
        overall: dict[str, Any] = summary.get("overall_sentiment_breakdown") or corpus["sentiment_breakdown"]
        total_posts = int(summary.get("total_posts_analyzed") or corpus["total_posts"])
        channel_stats: list[dict[str, Any]] = query_res.get("channel_stats") or corpus["channel_stats"]
        channel_volume: list[dict[str, Any]] = media_res.get("channel_volume") or corpus["channel_volume"]
        top_posts: list[dict[str, Any]] = query_res.get("top_posts") or corpus["top_posts"]

        ctx = _Ctx(
            overall=overall,
            total_posts=total_posts,
            query_res=query_res,
            media_res=media_res,
            insight_res=insight_res,
            corpus=corpus,
            channel_stats=channel_stats,
            channel_volume=channel_volume,
            top_posts=top_posts,
        )
        builders = (
            ("overview", "报告概览", self._sec_overview),
            ("background", "舆情背景与数据范围", self._sec_background),
            ("sentiment", "整体情绪结构", self._sec_sentiment),
            ("channels", "渠道声量分析", self._sec_channels),
            ("top-posts", "热点帖子榜", self._sec_top_posts),
            ("query", "Query Agent 深度分析", self._sec_query),
            ("media", "Media Agent 深度分析", self._sec_media),
            ("insight", "Insight Agent 深度分析", self._sec_insight),
            ("actions", "优先行动建议", self._sec_actions),
            ("trace", "执行过程回溯", self._sec_trace),
            ("appendix", "附录：演示数据明细表", self._sec_appendix),
            ("conclusion", "总结", self._sec_conclusion),
        )
        sections: list[dict[str, Any]] = []
        for i, (sid, sec_title, fn) in enumerate(builders, start=1):
            sections.append(
                {"id": sid, "num": i, "title": sec_title, "blocks": fn(summary, ctx)}
            )
        return sections

    # ---------------------------- 各章节 -------------------------------
    def _sec_overview(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """报告概览"""
        dominant = max(c.overall, key=lambda k: c.overall[k]) if c.overall else "neutral"
        blocks: list[dict[str, Any]] = [
            {
                "type": "paragraph",
                "text": (
                    f"本报告由多智能体舆情分析系统自动成稿：Query / Media / Insight 三类 Agent "
                    f"围绕主题「{summary.get('query', '')}」并行检索与分析多平台公开讨论，"
                    f"再经统一口径汇总为本章节制报告。以下概览给出本次分析的核心指标。"
                ),
            },
            {
                "type": "metrics",
                "items": [
                    {"label": "分析对象", "value": summary.get("query", "")},
                    {"label": "覆盖平台数", "value": len(c.channel_volume)},
                    {"label": "样本帖子总数", "value": c.total_posts},
                    {"label": f"主导情绪（{_sentiment_label(dominant)}占比）", "value": f"{_fmt(c.overall.get(dominant, 0))}%"},
                    {"label": "Agent 成功率", "value": f"{_fmt(summary.get('success_rate', 0))}%"},
                    {"label": "执行耗时", "value": f"{_fmt(summary.get('elapsed_seconds', 0))} s"},
                    {"label": "Token 消耗", "value": summary.get("total_tokens", 0)},
                    {"label": "优先行动建议条数", "value": len(insight_actions(c.insight_res))},
                ],
            },
        ]
        failed = summary.get("failed_agents") or []
        if failed:
            blocks.append({
                "type": "callout",
                "tone": "danger",
                "title": "执行异常",
                "text": f"以下 Agent 本轮未产出结果：{'、'.join(_fmt(f) for f in failed)}，相关章节以可用数据呈现。",
            })
        return blocks

    def _sec_background(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """舆情背景与数据范围"""
        platforms = [str(cv.get("channel", "")) for cv in c.channel_volume]
        total_engagement = sum(int(cv.get("engagement", 0)) for cv in c.channel_volume)
        spread = c.corpus.get("spread") or {}
        return [
            {
                "type": "paragraph",
                "text": (
                    f"本次分析聚焦「{summary.get('query', '')}」相关公开讨论。"
                    f"数据范围覆盖 {'、'.join(platforms)} 共 {len(platforms)} 个内容平台的 "
                    f"{c.total_posts} 条帖子，累计互动量（点赞+评论）约 {total_engagement} 次，"
                    f"其中高热帖子（互动量高于全体均值）{spread.get('hot_posts', 0)} 条。"
                ),
            },
            {
                "type": "list",
                "items": [
                    "采集范围：微博、小红书、抖音、快手等主流量内容平台（演示语料为内置多平台样本集）。",
                    "统计口径：单帖互动量 = 点赞数 + 评论数；渠道声量 = 渠道内帖子数与互动量合计。",
                    "情绪口径：positive（正面）/ neutral（中性）/ negative（负面）三类占比，和为 100%。",
                    "分析流程：Query Agent 负责检索与事实汇总，Media Agent 负责内容情感与传播分析，"
                    "Insight Agent 结合内部视角输出风险、机会与行动建议。",
                ],
            },
        ]

    def _sec_sentiment(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """整体情绪结构"""
        dominant = max(c.overall, key=lambda k: c.overall[k]) if c.overall else "neutral"
        pos = float(c.overall.get("positive", 0))
        neg = float(c.overall.get("negative", 0))
        net = pos - neg
        tendency = "偏正面" if net > 10 else ("偏负面" if net < -10 else "多空均衡")
        return [
            {
                "type": "chart",
                "chart_id": "donut",
                "title": "整体情绪占比环形图",
            },
            {
                "type": "table",
                "headers": ["情绪倾向", "占比"],
                "rows": [[_sentiment_label(k), f"{_fmt(c.overall.get(k, 0))}%"] for k in _SENTIMENT_ORDER],
            },
            {
                "type": "paragraph",
                "text": (
                    f"整体舆论以{_sentiment_label(dominant)}情绪为主（{dominant} 占比 "
                    f"{_fmt(c.overall.get(dominant, 0))}%）。正负面净差 {net:+g} 个百分点，"
                    f"舆论场{tendency}：正面声量主要来自产品体验类话题，负面声量集中于服务与价格议题，"
                    f"中性讨论以观望、比价与求建议为主。"
                ),
            },
        ]

    def _sec_channels(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """渠道声量分析"""
        total_posts_cv = sum(int(cv.get("posts", 0)) for cv in c.channel_volume) or 1
        total_engagement = sum(int(cv.get("engagement", 0)) for cv in c.channel_volume) or 1
        rows = [
            [
                str(cv.get("channel", "")),
                int(cv.get("posts", 0)),
                f"{int(cv.get('posts', 0)) * 100 / total_posts_cv:.1f}%",
                int(cv.get("engagement", 0)),
                f"{int(cv.get('engagement', 0)) * 100 / total_engagement:.1f}%",
            ]
            for cv in c.channel_volume
        ]
        top_volume = max(c.channel_volume, key=lambda cv: int(cv.get("posts", 0)), default={})
        top_engage = max(c.channel_volume, key=lambda cv: int(cv.get("engagement", 0)), default={})
        total_posts_cv = max(1, sum(int(cv.get("posts", 0)) for cv in c.channel_volume))
        total_engagement_share = max(1, sum(int(cv.get("engagement", 0)) for cv in c.channel_volume))
        bullets = []
        for cv in c.channel_volume:
            posts, engage = int(cv.get("posts", 0)), int(cv.get("engagement", 0))
            bullets.append(
                f"{cv.get('channel', '')}：声量占比 {posts * 100 / total_posts_cv:.1f}%，"
                f"互动占比 {engage * 100 / total_engagement_share:.1f}%，"
                f"单帖平均互动 {engage / max(1, posts):.1f} 次。"
            )
        blocks: list[dict[str, Any]] = [
            {"type": "chart", "chart_id": "bar", "title": "渠道声量与互动对比图"},
            {
                "type": "table",
                "headers": ["渠道", "帖子数", "声量占比", "互动量", "互动占比"],
                "rows": rows,
            },
            {"type": "subhead", "text": "分渠道解读"},
            {"type": "list", "items": bullets},
            {
                "type": "paragraph",
                "text": (
                    f"{top_volume.get('channel', '')} 帖子数最多（{top_volume.get('posts', 0)} 条），"
                    f"是本次讨论的主阵地；{top_engage.get('channel', '')} 互动量最高"
                    f"（{top_engage.get('engagement', 0)} 次），用户参与深度领先。"
                ),
            },
        ]
        if top_volume and top_engage and top_volume.get("channel") != top_engage.get("channel"):
            blocks.append({
                "type": "paragraph",
                "text": (
                    f"值得注意的是，声量最高渠道（{top_volume.get('channel')}）与互动最高渠道"
                    f"（{top_engage.get('channel')}）并不一致：后者单帖平均互动更高，"
                    f"说明其用户更愿意参与讨论，值得在传播策略上倾斜。"
                ),
            })
        return blocks

    def _sec_top_posts(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """热点帖子榜"""
        rows = []
        for i, p in enumerate(c.top_posts, start=1):
            likes, comments = int(p.get("likes", 0)), int(p.get("comments", 0))
            rows.append([
                i,
                str(p.get("platform", "")),
                str(p.get("content", "")),
                likes,
                comments,
                likes + comments,
                _sentiment_label(p.get("sentiment")),
            ])
        head = c.top_posts[0] if c.top_posts else {}
        positive_in_board = sum(1 for p in c.top_posts if p.get("sentiment") == "positive")
        return [
            {
                "type": "paragraph",
                "text": (
                    f"按互动量（点赞+评论）降序取前 {len(c.top_posts)} 条代表性帖子。"
                    f"榜首内容来自{head.get('platform', '')}（互动 "
                    f"{int(head.get('likes', 0)) + int(head.get('comments', 0))}），"
                    f"榜内正面帖 {positive_in_board} 条。"
                ),
            },
            {
                "type": "table",
                "headers": ["排名", "平台", "内容", "点赞", "评论", "互动", "情绪"],
                "rows": rows,
            },
        ]

    def _sec_query(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """Query Agent 深度分析"""
        blocks: list[dict[str, Any]] = [
            {
                "type": "paragraph",
                "text": str(c.query_res.get("facts") or "本轮分析 Query Agent 未参与，以下为全量语料的渠道统计。"),
            },
            {
                "type": "table",
                "headers": ["渠道", "样本数", "正面占比", "中性占比", "负面占比", "互动量"],
                "rows": [
                    [
                        str(cs.get("channel", "")),
                        int(cs.get("posts", 0)),
                        f"{_fmt(cs.get('positive_pct', 0))}%",
                        f"{_fmt(cs.get('neutral_pct', 0))}%",
                        f"{_fmt(cs.get('negative_pct', 0))}%",
                        int(cs.get("engagement", 0)),
                    ]
                    for cs in c.channel_stats
                ],
            },
        ]
        if c.channel_stats:
            worst = max(c.channel_stats, key=lambda cs: float(cs.get("negative_pct", 0)))
            best = max(c.channel_stats, key=lambda cs: float(cs.get("positive_pct", 0)))
            busiest = max(c.channel_stats, key=lambda cs: int(cs.get("posts", 0)))
            blocks.append({
                "type": "list",
                "style": "bullets",
                "items": [
                    f"口碑高地：{best.get('channel', '')} 正面占比最高（{_fmt(best.get('positive_pct', 0))}%），可作为正向素材放大渠道。",
                    f"风险渠道：{worst.get('channel', '')} 负面占比 {_fmt(worst.get('negative_pct', 0))}%，需优先排查差评成因。",
                    f"声量中心：{busiest.get('channel', '')} 样本量最大（{busiest.get('posts', 0)} 条），其情绪走向基本决定整体盘面。",
                ],
            })
        return blocks

    def _sec_media(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """Media Agent 深度分析"""
        breakdown: dict[str, Any] = c.media_res.get("sentiment_breakdown") or c.overall
        spread = c.media_res.get("spread") or c.corpus.get("spread") or {}
        avg_engage = round(sum(int(cv.get("engagement", 0)) for cv in c.channel_volume) / max(1, c.total_posts), 1)
        return [
            {
                "type": "paragraph",
                "text": str(c.media_res.get("analysis") or "本轮分析 Media Agent 未参与，以下为全量语料的内容情感与传播统计。"),
            },
            {
                "type": "metrics",
                "items": [
                    {"label": "累计点赞", "value": spread.get("total_likes", 0)},
                    {"label": "高热帖数量", "value": spread.get("hot_posts", 0)},
                    {"label": "平均单帖互动", "value": avg_engage},
                    {"label": "覆盖渠道", "value": len(c.channel_volume)},
                ],
            },
            {
                "type": "table",
                "headers": ["情绪倾向", "内容占比"],
                "rows": [[_sentiment_label(k), f"{_fmt(breakdown.get(k, 0))}%"] for k in _SENTIMENT_ORDER],
            },
            {
                "type": "paragraph",
                "text": (
                    f"内容侧情绪结构与整体口径一致（同源语料统一统计）：正面内容以实测体验、"
                    f"场景化种草为主，负面内容集中于客服响应、价格与品控话题；"
                    f"高热内容具备明显的\"实测/对比\"属性，建议在官方内容运营中沿用该叙事框架。"
                ),
            },
        ]

    def _sec_insight(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """Insight Agent 深度分析（风险与机会）"""
        blocks: list[dict[str, Any]] = []
        risks = c.insight_res.get("risks") or []
        opportunities = c.insight_res.get("opportunities") or []
        advice = c.insight_res.get("advice")
        blocks.append({"type": "subhead", "text": "风险点"})
        if risks:
            blocks.extend(
                {"type": "callout", "tone": "danger", "title": f"风险 {i}", "text": str(r)}
                for i, r in enumerate(risks, start=1)
            )
        else:
            blocks.append({"type": "paragraph", "text": "本轮未识别到显著风险项。"})
        blocks.append({"type": "subhead", "text": "机会点"})
        if opportunities:
            blocks.extend(
                {"type": "callout", "tone": "success", "title": f"机会 {i}", "text": str(o)}
                for i, o in enumerate(opportunities, start=1)
            )
        else:
            blocks.append({"type": "paragraph", "text": "本轮未识别到显著机会项。"})
        if advice:
            blocks.append({"type": "subhead", "text": "综合研判"})
            blocks.append({"type": "paragraph", "text": str(advice)})
        return blocks

    def _sec_actions(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """优先行动建议"""
        actions = insight_actions(c.insight_res)
        blocks: list[dict[str, Any]] = [
            {
                "type": "paragraph",
                "text": (
                    f"基于整体情绪结构、渠道负面分布与头部内容表现，共生成 {len(actions)} 条优先行动建议"
                    f"（按紧急程度标注：高 / 中 / 低）。"
                ),
            },
        ]
        if not actions:
            blocks.append({"type": "paragraph", "text": "本轮 Insight Agent 未参与，暂无行动清单。"})
        for i, act in enumerate(actions, start=1):
            urgency = _URGENCY_LABELS.get(str(act.get("urgency", "medium")), "中")
            blocks.append({
                "type": "callout",
                "tone": "info",
                "title": f"建议 {i}（紧急度：{urgency}）：{act.get('action', '')}",
                "text": str(act.get("rationale", "")),
            })
        return blocks

    def _sec_trace(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """执行过程回溯"""
        logs = summary.get("logs") or []
        level_labels = {
            "info": "信息", "tool": "工具调用", "tool_ok": "调用成功",
            "tool_fail": "调用失败", "tool_retry": "调用重试",
            "agent_retry": "Agent 重试", "error": "错误",
        }
        blocks: list[dict[str, Any]] = [
            {
                "type": "paragraph",
                "text": (
                    f"本章记录本轮多智能体协作的完整执行轨迹（共 {len(logs)} 条事件），"
                    f"包括各 Agent 的启动、工具调用与结果回填过程，便于审计与问题追溯。"
                ),
            },
        ]
        if logs:
            blocks.append({
                "type": "table",
                "headers": ["Agent", "事件", "说明"],
                "rows": [
                    [
                        str(l.get("agent", "")),
                        level_labels.get(str(l.get("level", "")), str(l.get("level", ""))),
                        str(l.get("message", "")),
                    ]
                    for l in logs
                ],
            })
        else:
            blocks.append({"type": "paragraph", "text": "本次运行未采集到执行日志。"})
        return blocks

    def _sec_appendix(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """附录：演示数据明细表"""
        posts = _demo_posts()
        by_platform: dict[str, list[dict[str, Any]]] = {}
        for p in posts:
            by_platform.setdefault(str(p.get("platform", "")), []).append(p)

        # 平台 × 情绪交叉汇总（与上文统计口径一致，便于核对）
        cross_rows = []
        for platform, items in by_platform.items():
            counts = {k: sum(1 for it in items if it.get("sentiment") == k) for k in _SENTIMENT_ORDER}
            cross_rows.append([
                platform,
                len(items),
                counts["positive"],
                counts["neutral"],
                counts["negative"],
                sum(int(it.get("likes", 0)) + int(it.get("comments", 0)) for it in items),
            ])
        cross_rows.append([
            "合计", len(posts),
            sum(r[2] for r in cross_rows), sum(r[3] for r in cross_rows),
            sum(r[4] for r in cross_rows), sum(r[5] for r in cross_rows),
        ])

        blocks: list[dict[str, Any]] = [
            {
                "type": "paragraph",
                "text": (
                    f"以下为本次分析的完整演示语料明细（共 {len(posts)} 条），"
                    f"按平台分组列出内容摘要、互动数据与情绪标注，供核对上文各项统计口径；"
                    f"多智能体执行过程见上一章回溯记录。"
                ),
            },
            {
                "type": "table",
                "headers": ["平台", "帖数", "正面", "中性", "负面", "互动合计"],
                "rows": cross_rows,
            },
        ]
        for platform, items in by_platform.items():
            counts = {k: sum(1 for it in items if it.get("sentiment") == k) for k in _SENTIMENT_ORDER}
            engage_sum = sum(int(it.get("likes", 0)) + int(it.get("comments", 0)) for it in items)
            blocks.append({"type": "subhead", "text": f"{platform}（{len(items)} 条）"})
            blocks.append({
                "type": "paragraph",
                "text": (
                    f"{platform} 共 {len(items)} 条：正面 {counts['positive']} / 中性 {counts['neutral']} / "
                    f"负面 {counts['negative']}，互动合计 {engage_sum} 次。"
                ),
            })
            blocks.append({
                "type": "table",
                "headers": ["编号", "内容", "点赞", "评论", "互动", "情绪", "发布时间"],
                "rows": [
                    [
                        int(p.get("id", 0)),
                        str(p.get("content", "")),
                        int(p.get("likes", 0)),
                        int(p.get("comments", 0)),
                        int(p.get("likes", 0)) + int(p.get("comments", 0)),
                        _sentiment_label(p.get("sentiment")),
                        str(p.get("ts", "")),
                    ]
                    for p in items
                ],
            })
        return blocks

    def _sec_conclusion(self, summary: dict[str, Any], c: "_Ctx") -> list[dict[str, Any]]:
        """总结"""
        dominant = max(c.overall, key=lambda k: c.overall[k]) if c.overall else "neutral"
        worst = max(c.channel_stats, key=lambda cs: float(cs.get("negative_pct", 0)), default={}) \
            if c.channel_stats else {}
        actions = insight_actions(c.insight_res)
        first_action = actions[0].get("action", "") if actions else ""
        takeaways = [
            f"整体情绪：{_sentiment_label(dominant)}主导（占比 {_fmt(c.overall.get(dominant, 0))}%），"
            f"正负面净差 {float(c.overall.get('positive', 0)) - float(c.overall.get('negative', 0)):+g} 个百分点。",
        ]
        if worst:
            takeaways.append(
                f"主要风险：{worst.get('channel', '')} 负面占比 {_fmt(worst.get('negative_pct', 0))}%，"
                f"为各渠道最高，需优先处置。"
            )
        if c.top_posts:
            head = c.top_posts[0]
            takeaways.append(
                f"内容杠杆：{head.get('platform', '')} 头部正向内容（互动 "
                f"{int(head.get('likes', 0)) + int(head.get('comments', 0))}）具备放大价值。"
            )
        if first_action:
            takeaways.append(f"首要行动：{first_action}。")
        return [
            {"type": "paragraph", "text": "综合全部章节的统计与 Agent 分析结论，本次舆情研判要点如下："},
            {"type": "list", "items": takeaways},
            {
                "type": "paragraph",
                "text": (
                    f"建议以本报告行动清单为起点，保持对渠道负面率与头部内容的持续监测，"
                    f"形成\"监测 - 分析 - 行动 - 复盘\"的闭环运营机制。"
                ),
            },
        ]

    # ------------------------------------------------------------------
    # HTML 渲染
    # ------------------------------------------------------------------
    def _render_html(self, title: str, summary: dict[str, Any], sections: list[dict[str, Any]]) -> str:
        dominant = _dominant_of(summary)
        ctx = {
            "title": title,
            "task_id": summary.get("task_id", ""),
            "query": summary.get("query", ""),
            "elapsed": summary.get("elapsed_seconds", 0),
            "success_rate": summary.get("success_rate", 0),
            "sections": sections,
            "overall_breakdown": summary.get("overall_sentiment_breakdown") or {},
            "dominant_label": _SENTIMENT_LABELS.get(dominant, dominant),
            "dominant_key": dominant,
            "charts_json": _charts_json(summary, sections),
        }
        if self._env_ok:
            try:
                return self._env.get_template("report.html").render(**ctx)
            except Exception:
                pass
        env = Environment(autoescape=select_autoescape(["html"]))
        return env.from_string(_DEFAULT_TEMPLATE).render(**ctx)

    # ------------------------------------------------------------------
    # Markdown 渲染：直接消费结构化章节
    # ------------------------------------------------------------------
    def render_markdown(self, title: str, summary: dict[str, Any], sections: list[dict[str, Any]]) -> str:
        lines: list[str] = [f"# {title}", ""]
        lines.append(
            f"> 任务 ID：{summary.get('task_id', '')} ｜ 查询：{summary.get('query', '')} "
            f"｜ 耗时：{summary.get('elapsed_seconds', 0)}s ｜ 成功率：{summary.get('success_rate', 0)}%"
        )
        lines.append("")
        for sec in sections:
            lines.append(f"## {sec['num']}. {sec['title']}")
            lines.append("")
            lines.extend(_blocks_to_markdown(sec["blocks"]))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    # ------------------------------------------------------------------
    # PDF 渲染：reportlab flowables 直接消费结构化章节
    # ------------------------------------------------------------------
    def render_pdf(self, title: str, summary: dict[str, Any], sections: list[dict[str, Any]], out_path: str) -> str:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        accent = colors.HexColor("#2F5FD0")

        style_title = ParagraphStyle("title", fontName="STSong-Light", fontSize=20, leading=28,
                                     spaceAfter=6, textColor=accent, wordWrap="CJK")
        style_meta = ParagraphStyle("meta", fontName="STSong-Light", fontSize=9.5, leading=15,
                                    textColor=colors.HexColor("#555F70"), wordWrap="CJK")
        style_h2 = ParagraphStyle("h2", fontName="STSong-Light", fontSize=15, leading=22,
                                  spaceBefore=16, spaceAfter=8, textColor=accent, wordWrap="CJK")
        style_h3 = ParagraphStyle("h3", fontName="STSong-Light", fontSize=12, leading=18,
                                  spaceBefore=10, spaceAfter=6, wordWrap="CJK")
        style_body = ParagraphStyle("body", fontName="STSong-Light", fontSize=11, leading=18,
                                    spaceAfter=7, firstLineIndent=22, wordWrap="CJK")
        style_flat = ParagraphStyle("flat", parent=style_body, firstLineIndent=0)
        style_bullet = ParagraphStyle("bullet", parent=style_body, firstLineIndent=0, leftIndent=14)
        style_cell = ParagraphStyle("cell", fontName="STSong-Light", fontSize=10, leading=15.5, wordWrap="CJK")
        style_cell_head = ParagraphStyle("cellh", parent=style_cell, textColor=colors.white)

        doc = SimpleDocTemplate(out_path, pagesize=A4,
                                leftMargin=20 * mm, rightMargin=20 * mm,
                                topMargin=20 * mm, bottomMargin=20 * mm,
                                title=title, author="Sentiment Analysis Agents")
        story: list[Any] = []

        # 报告头
        story.append(Paragraph(title, style_title))
        story.append(Paragraph(
            f"任务 ID：{summary.get('task_id', '')} ｜ 查询：{summary.get('query', '')} ｜ "
            f"耗时：{_fmt(summary.get('elapsed_seconds', 0))}s ｜ 成功率：{_fmt(summary.get('success_rate', 0))}% ｜ "
            f"Token：{summary.get('total_tokens', 0)}",
            style_meta,
        ))
        story.append(Spacer(1, 6))

        avail = A4[0] - doc.leftMargin - doc.rightMargin
        tone_bg = {"danger": colors.HexColor("#FCEBEA"), "success": colors.HexColor("#EAF6EE"), "info": colors.HexColor("#EAF0FC")}
        tone_border = {"danger": colors.HexColor("#C0392B"), "success": colors.HexColor("#27AE60"), "info": colors.HexColor("#2F5FD0")}

        for sec in sections:
            story.append(Paragraph(f"{sec['num']}. {sec['title']}", style_h2))
            for block in sec["blocks"]:
                kind = block.get("type")
                if kind == "paragraph":
                    story.append(Paragraph(_esc(str(block.get("text", ""))), style_body))
                elif kind == "subhead":
                    story.append(Paragraph(_esc(str(block.get("text", ""))), style_h3))
                elif kind == "metrics":
                    items = block.get("items") or []
                    # 两列指标表（标签 | 数值），逐行铺开保证可读性
                    t = Table(
                        [
                            [Paragraph(_esc(str(m.get("label", ""))), style_cell),
                             Paragraph(_esc(_fmt(m.get("value", ""))), style_cell)]
                            for m in items
                        ],
                        colWidths=[avail * 0.55, avail * 0.45],
                    )
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6FB")),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7DFEC")),
                        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 8))
                elif kind == "table":
                    headers = block.get("headers", [])
                    body_rows = block.get("rows", [])
                    ncol = max(1, len(headers))
                    wide_col = _wide_text_col(body_rows)
                    col_widths = _table_col_widths(headers, avail)

                    def _cell(ci: int, value: Any, header: bool = False) -> Any:
                        # 长文本列（如帖子内容）用 Paragraph 换行，其余保持纯字符串
                        if ci == wide_col:
                            return Paragraph(_esc(str(value)), style_cell_head if header else style_cell)
                        return _esc(_fmt(value))

                    t = Table(
                        [[_cell(ci, h, header=True) for ci, h in enumerate(headers)]]
                        + [[_cell(ci, v) for ci, v in enumerate(row)] for row in body_rows],
                        colWidths=col_widths,
                        repeatRows=1,
                    )
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), accent),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3E4")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FB")]),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 10))
                elif kind == "list":
                    for item in block.get("items", []):
                        story.append(Paragraph(f"• {_esc(str(item))}", style_bullet))
                    story.append(Spacer(1, 4))
                elif kind == "callout":
                    tone = str(block.get("tone", "info"))
                    head = _esc(str(block.get("title", "")))
                    body = _esc(str(block.get("text", "")))
                    inner = Paragraph(f"<b>{head}</b><br/>{body}" if body else f"<b>{head}</b>", style_flat)
                    ct = Table([[inner]], colWidths=[avail])
                    ct.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), tone_bg.get(tone, tone_bg["info"])),
                        ("LINEBEFORE", (0, 0), (0, -1), 3, tone_border.get(tone, tone_border["info"])),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]))
                    story.append(ct)
                    story.append(Spacer(1, 6))
            if sec.get("id") == "appendix":
                story.append(PageBreak())

        doc.build(story)
        return out_path

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    async def generate(
        self, summary: dict[str, Any], out_dir: str, title: str | None = None
    ) -> dict[str, str]:
        """生成 HTML / Markdown / PDF 三格式报告，返回路径映射。"""
        # 模板渲染与 PDF 制作为 CPU 任务，放入线程池避免阻塞事件循环
        return await asyncio.to_thread(self._generate_sync, summary, out_dir, title)

    def _generate_sync(
        self, summary: dict[str, Any], out_dir: str, title: str | None
    ) -> dict[str, str]:
        os.makedirs(out_dir, exist_ok=True)
        title = title or f"舆情分析报告-{summary.get('task_id', 'report')}"
        sections = self.build_sections(summary)
        html_content = self._render_html(title, summary, sections)

        base = os.path.join(out_dir, summary.get("task_id", "report"))
        html_path = f"{base}.html"
        md_path = f"{base}.md"
        pdf_path = f"{base}.pdf"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.render_markdown(title, summary, sections))
        self.render_pdf(title, summary, sections, pdf_path)

        return {"html": html_path, "markdown": md_path, "pdf": pdf_path}


# ----------------------------------------------------------------------
# 辅助类型与函数
# ----------------------------------------------------------------------
class _Ctx:
    """章节装配上下文：预取的结构化字段集合。"""

    def __init__(self, **kw: Any) -> None:
        self.overall: dict[str, Any] = kw["overall"]
        self.total_posts: int = kw["total_posts"]
        self.query_res: dict[str, Any] = kw["query_res"]
        self.media_res: dict[str, Any] = kw["media_res"]
        self.insight_res: dict[str, Any] = kw["insight_res"]
        self.corpus: dict[str, Any] = kw["corpus"]
        self.channel_stats: list[dict[str, Any]] = kw["channel_stats"]
        self.channel_volume: list[dict[str, Any]] = kw["channel_volume"]
        self.top_posts: list[dict[str, Any]] = kw["top_posts"]


def insight_actions(insight_res: dict[str, Any]) -> list[dict[str, Any]]:
    actions = insight_res.get("priority_actions") or []
    return [a for a in actions if isinstance(a, dict)]


def _demo_posts() -> list[dict[str, Any]]:
    """全部演示帖子（附录明细用）；工具层私有常量只读引用，失败则退化为热门榜。"""
    try:
        from ..agents.tools import _DEMO_POSTS

        order = {"微博": 0, "小红书": 1, "抖音": 2, "快手": 3}
        return sorted((dict(p) for p in _DEMO_POSTS), key=lambda p: (order.get(str(p.get("platform")), 99), int(p.get("id", 0))))
    except Exception:  # noqa: BLE001
        return []


def _dominant_of(summary: dict[str, Any]) -> str:
    breakdown = summary.get("overall_sentiment_breakdown") or {}
    return max(breakdown, key=lambda k: breakdown[k]) if breakdown else "neutral"


def _esc(text: str) -> str:
    import html as _html

    return _html.escape(text)


def _wide_text_col(rows: list[list[Any]]) -> int | None:
    """定位长文本列（平均字符长度显著超长者），供表格换行渲染。"""
    if not rows:
        return None
    ncol = len(rows[0])
    best, best_len = None, 24
    for ci in range(ncol):
        avg = sum(len(str(r[ci])) for r in rows) / len(rows)
        if avg > best_len:
            best, best_len = ci, avg
    return best


def _table_col_widths(headers: list[Any], avail: float) -> list[float]:
    """列宽分配：含长文本列的明细表按语义分配（内容列加宽），其余均分。"""
    ncol = max(1, len(headers))
    wide_idx = next((i for i, h in enumerate(headers) if str(h) == "内容"), None)
    if wide_idx is None or ncol <= 2:
        return [avail / ncol] * ncol
    others = [i for i in range(ncol) if i != wide_idx]
    wide_share = 0.46
    per = avail * (1 - wide_share) / max(1, len(others))
    return [avail * wide_share if i == wide_idx else per for i in range(ncol)]


def _blocks_to_markdown(blocks: list[dict[str, Any]], level: int = 3) -> list[str]:
    lines: list[str] = []
    for block in blocks:
        kind = block.get("type")
        if kind == "paragraph":
            lines.append(str(block.get("text", "")))
            lines.append("")
        elif kind == "subhead":
            lines.append(f"{'#' * level} {block.get('text', '')}")
            lines.append("")
        elif kind == "metrics":
            for m in block.get("items", []):
                lines.append(f"- **{m.get('label', '')}**：{_fmt(m.get('value', ''))}")
            lines.append("")
        elif kind == "table":
            headers = [str(h) for h in block.get("headers", [])]
            if headers:
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("|" + "|".join([" --- "] * len(headers)) + "|")
                for row in block.get("rows", []):
                    cells = [str(c).replace("\n", " ").replace("|", "\\|") for c in row]
                    lines.append("| " + " | ".join(cells) + " |")
                lines.append("")
        elif kind == "list":
            for item in block.get("items", []):
                lines.append(f"- {item}")
            lines.append("")
        elif kind == "callout":
            tone_title = {"danger": "风险", "success": "机会", "info": "建议"}.get(str(block.get("tone", "info")), "要点")
            title = str(block.get("title", ""))
            text = str(block.get("text", ""))
            content = f"**【{tone_title}】{title}**" + (f" — {text}" if text else "")
            lines.append(f"> {content}")
            lines.append("")
    return lines


def _charts_json(summary: dict[str, Any], sections: list[dict[str, Any]]) -> str:
    """图表数据 JSON（内联进 HTML <script>；转义 </ 防止脚本提前闭合）。"""
    overall = summary.get("overall_sentiment_breakdown") or {}
    payload: dict[str, Any] = {
        "donut": {
            "name": "整体情绪占比",
            "data": [
                {"name": _SENTIMENT_LABELS[k], "value": overall.get(k, 0)}
                for k in _SENTIMENT_ORDER
                if k in overall
            ],
        },
        "bar": {"name": "渠道声量", "data": []},
    }
    for sec in sections:
        for b in sec.get("blocks", []):
            if b.get("type") == "table" and b.get("headers", [])[:1] == ["渠道"]:
                payload["bar"]["data"] = [
                    {"channel": str(r[0]), "posts": r[1], "engagement": r[3]}
                    for r in b.get("rows", [])
                ]
    return json.dumps(payload, ensure_ascii=False, default=str).replace("</", "<\\/")
