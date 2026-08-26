"""Query / Media / Insight 三类 Agent 的实现。"""
from __future__ import annotations

from typing import Any

from ..config import Settings
from .base import AgentContext, BaseAgent
from .tools import ToolRegistry, demo_corpus_stats


class QueryAgent(BaseAgent):
    """Query Agent：精准信息搜索 —— 检索多平台帖子、解析文档，汇总事实。"""

    name = "query"
    role_prompt = (
        "你是信息检索专员。使用 search_posts / parse_document 工具搜集与用户问题相关的"
        "舆情信息，并输出结构化的事实摘要：包括信息渠道、核心事实、相关帖子。"
    )

    def __init__(self, llm: Any, tools: ToolRegistry, settings: Settings | None = None) -> None:
        super().__init__(llm, settings)
        for name in ("search_posts", "parse_document"):
            spec = next(s for s in tools.specs() if s["name"] == name)
            self.register_tool(name, spec["description"], spec["parameters"], tools.get(name))

    def _summarize(self, ctx: AgentContext, reply: str) -> dict[str, Any]:
        # 渠道统计与热门帖子从演示数据源真实统计得出（口径统一，见 tools.demo_corpus_stats）
        stats = demo_corpus_stats()
        return {
            "agent": self.name,
            "channels": ["微博", "小红书", "抖音", "快手"],
            "facts": reply,
            "channel_stats": stats["channel_stats"],
            "top_posts": stats["top_posts"],
        }


class MediaAgent(BaseAgent):
    """Media Agent：多模态内容分析 —— 分析图文/视频内容的情感与传播。"""

    name = "media"
    role_prompt = (
        "你是多模态内容分析师。使用 query_db / sentiment_analysis 工具分析帖子内容，"
        "输出结构化摘要：情感分布、传播热度、代表性内容。"
    )

    def __init__(self, llm: Any, tools: ToolRegistry, settings: Settings | None = None) -> None:
        super().__init__(llm, settings)
        for name in ("query_db", "sentiment_analysis"):
            spec = next(s for s in tools.specs() if s["name"] == name)
            self.register_tool(name, spec["description"], spec["parameters"], tools.get(name))

    def _summarize(self, ctx: AgentContext, reply: str) -> dict[str, Any]:
        # 情绪占比 / 渠道声量 / 传播热度均从帖子数据真实统计（spread 字段语义不变）
        stats = demo_corpus_stats()
        return {
            "agent": self.name,
            "sentiment": "neutral",
            "spread": stats["spread"],
            "analysis": reply,
            "sentiment_breakdown": stats["sentiment_breakdown"],
            "channel_volume": stats["channel_volume"],
        }


class InsightAgent(BaseAgent):
    """Insight Agent：私有数据库挖掘 —— 结合内部数据给出深层洞察与建议。"""

    name = "insight"
    role_prompt = (
        "你是资深舆情分析师。使用 query_db / sentiment_analysis 工具结合内部业务数据，"
        "输出结构化摘要：风险点、机会点、行动建议。"
    )

    def __init__(self, llm: Any, tools: ToolRegistry, settings: Settings | None = None) -> None:
        super().__init__(llm, settings)
        for name in ("query_db", "sentiment_analysis"):
            spec = next(s for s in tools.specs() if s["name"] == name)
            self.register_tool(name, spec["description"], spec["parameters"], tools.get(name))

    def _priority_actions(self, stats: dict[str, Any]) -> list[dict[str, str]]:
        """按整体情绪、渠道负面率、头部帖互动与声量缺口生成优先行动清单。"""
        breakdown = stats["sentiment_breakdown"]
        channels = sorted(
            stats["channel_stats"],
            key=lambda c: (-c["negative_pct"], -c["engagement"]),
        )
        worst_channel = channels[0] if channels else None
        quiet_channel = min(stats["channel_volume"], key=lambda c: c["posts"], default=None)
        top_post = stats["top_posts"][0] if stats["top_posts"] else None

        actions: list[dict[str, str]] = [
            {
                "action": "启动负面舆情专项响应，48 小时内复核售后与价格类差评工单",
                "rationale": f"整体负面声量占比 {breakdown['negative']}%，集中在客服响应与价格争议议题",
                "urgency": "high" if breakdown["negative"] >= 30 else "medium",
            }
        ]
        if worst_channel and worst_channel["negative_pct"] > 0:
            actions.append(
                {
                    "action": f"针对{worst_channel['channel']}开展定向口碑修复与用户沟通",
                    "rationale": (
                        f"{worst_channel['channel']}负面占比 {worst_channel['negative_pct']}%、"
                        f"互动量 {worst_channel['engagement']}，为负面扩散高风险渠道"
                    ),
                    "urgency": "high" if worst_channel["negative_pct"] >= 40 else "medium",
                }
            )
        if top_post:
            actions.append(
                {
                    "action": f"放大{top_post['platform']}头部正向内容的传播（投放联动/官方转发）",
                    "rationale": (
                        f"最高互动帖来自{top_post['platform']}"
                        f"（赞 {top_post['likes']}、评 {top_post['comments']}），情绪为{top_post['sentiment']}"
                    ),
                    "urgency": "medium",
                }
            )
        if quiet_channel:
            actions.append(
                {
                    "action": f"补充{quiet_channel['channel']}的声量监测与内容投放",
                    "rationale": (
                        f"{quiet_channel['channel']}样本仅 {quiet_channel['posts']} 条、"
                        f"互动量 {quiet_channel['engagement']}，存在监测盲区与增长空间"
                    ),
                    "urgency": "low",
                }
            )
        return actions

    def _summarize(self, ctx: AgentContext, reply: str) -> dict[str, Any]:
        # 优先行动清单由真实统计数据推导（非硬编码常数）
        stats = demo_corpus_stats()
        return {
            "agent": self.name,
            "risks": ["客服响应慢可能引发负面扩散"],
            "opportunities": ["产品口碑正向，可加大推广"],
            "advice": reply,
            "priority_actions": self._priority_actions(stats),
        }


def build_agents(
    llm: Any, tools: ToolRegistry, settings: Settings | None = None
) -> dict[str, BaseAgent]:
    """构建三类 Agent（Query / Media / Insight）。"""
    return {
        "query": QueryAgent(llm, tools, settings),
        "media": MediaAgent(llm, tools, settings),
        "insight": InsightAgent(llm, tools, settings),
    }
