"""4 类 Function Calling 工具：检索 / 文档解析 / 数据库查询 / 情感分析。

每个工具注册为 (描述, 参数 JSON Schema, 异步执行函数)，供三类 Agent 共享；
工具层负责执行真实逻辑（此处为可运行的轻量实现 + 内存数据源），
LLM 通过 tool_calls 选择工具，由 Agent 循环执行并把结果回填给模型。
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

# 内置演示数据源（可替换为 MindSpider 抓取 / 数据库查询）。
# 字段：id / platform / content / likes / comments / sentiment(positive|neutral|negative) / ts
_DEMO_POSTS: list[dict[str, Any]] = [
    # ---- 微博 ----
    {"id": 1, "platform": "微博", "content": "星云X1到手一周，续航是真的顶，重度使用一天还剩三成电，五星好评！", "likes": 520, "comments": 86, "sentiment": "positive", "ts": "2026-08-01 10:00"},
    {"id": 2, "platform": "微博", "content": "客服态度差，等了一小时没人理，问题也没解决，差评。", "likes": 189, "comments": 132, "sentiment": "negative", "ts": "2026-08-01 11:00"},
    {"id": 3, "platform": "微博", "content": "发布会看了，参数中规中矩，价格公布之前先观望。", "likes": 96, "comments": 41, "sentiment": "neutral", "ts": "2026-08-01 12:00"},
    {"id": 4, "platform": "微博", "content": "售后响应及时，屏幕的问题两天就给解决了，满意。", "likes": 233, "comments": 35, "sentiment": "positive", "ts": "2026-08-01 15:00"},
    {"id": 5, "platform": "微博", "content": "首发就涨价，背刺老用户，真的寒心，已劝退身边三个朋友。", "likes": 305, "comments": 178, "sentiment": "negative", "ts": "2026-08-02 09:20"},
    {"id": 6, "platform": "微博", "content": "转发抽奖抽星云X1，试试运气，中了就来晒单。", "likes": 77, "comments": 152, "sentiment": "neutral", "ts": "2026-08-02 13:45"},
    {"id": 7, "platform": "微博", "content": "夜拍实测：夜景模式比上一代强太多，色彩很讨喜，喜欢。", "likes": 462, "comments": 98, "sentiment": "positive", "ts": "2026-08-02 20:10"},
    {"id": 8, "platform": "微博", "content": "系统更新后发热明显，打游戏烫手，希望官方尽快出补丁修复。", "likes": 148, "comments": 90, "sentiment": "negative", "ts": "2026-08-03 11:30"},
    # ---- 小红书 ----
    {"id": 9, "platform": "小红书", "content": "颜值党狂喜！新配色太绝了，上手轻巧，女生单手握持无压力，种草！", "likes": 688, "comments": 210, "sentiment": "positive", "ts": "2026-08-01 12:00"},
    {"id": 10, "platform": "小红书", "content": "性价比一般，但颜值在线，纠结配色中，到底要不要入手？在线等。", "likes": 154, "comments": 66, "sentiment": "neutral", "ts": "2026-08-01 14:30"},
    {"id": 11, "platform": "小红书", "content": "拍了下午照片机身就发热，镜头还有进灰，退货流程又慢，体验很差。", "likes": 201, "comments": 143, "sentiment": "negative", "ts": "2026-08-02 16:00"},
    {"id": 12, "platform": "小红书", "content": "通勤一个月使用报告：信号稳、充电快，地铁上刷视频不掉链子，推荐。", "likes": 430, "comments": 87, "sentiment": "positive", "ts": "2026-08-02 18:40"},
    {"id": 13, "platform": "小红书", "content": "对比了两款竞品各有优劣，主要看中影像，再等等大促价格。", "likes": 122, "comments": 58, "sentiment": "neutral", "ts": "2026-08-03 10:15"},
    {"id": 14, "platform": "小红书", "content": "直播间说好送耳机，到手没有，客服互相推诿，避雷。", "likes": 266, "comments": 190, "sentiment": "negative", "ts": "2026-08-03 14:50"},
    {"id": 15, "platform": "小红书", "content": "学生党福音，以旧换新补贴后真香，室友们都被我安利了。", "likes": 355, "comments": 74, "sentiment": "positive", "ts": "2026-08-03 21:05"},
    # ---- 抖音 ----
    {"id": 16, "platform": "抖音", "content": "实测三天：续航不错、屏幕跟手，就是有点重，总体瑕不掩瑜。", "likes": 890, "comments": 320, "sentiment": "positive", "ts": "2026-08-01 13:00"},
    {"id": 17, "platform": "抖音", "content": "开箱视频来了，先看外观，性能长测后续再更，先蹲个热度。", "likes": 512, "comments": 264, "sentiment": "neutral", "ts": "2026-08-01 19:25"},
    {"id": 18, "platform": "抖音", "content": "塑料边框卖这个价格？诚意不足，劝退，不推荐入手。", "likes": 640, "comments": 411, "sentiment": "negative", "ts": "2026-08-02 12:10"},
    {"id": 19, "platform": "抖音", "content": "游戏实测帧率拉满不降频，这次散热是真下功夫了，点赞。", "likes": 720, "comments": 233, "sentiment": "positive", "ts": "2026-08-02 21:35"},
    {"id": 20, "platform": "抖音", "content": "网友说它撞脸友商设计，你们觉得像吗？评论区聊聊。", "likes": 388, "comments": 502, "sentiment": "neutral", "ts": "2026-08-03 08:55"},
    {"id": 21, "platform": "抖音", "content": "直播翻车现场：主播承诺的赠品不兑现，评论区已经炸了。", "likes": 455, "comments": 366, "sentiment": "negative", "ts": "2026-08-03 19:40"},
    {"id": 22, "platform": "抖音", "content": "给爸妈各买了一台，大字模式和远程协助太贴心，全家满意。", "likes": 601, "comments": 145, "sentiment": "positive", "ts": "2026-08-04 09:10"},
    # ---- 快手 ----
    {"id": 23, "platform": "快手", "content": "老铁们这手机值不值？预算两千五，懂行的给点意见。", "likes": 176, "comments": 133, "sentiment": "neutral", "ts": "2026-08-01 14:00"},
    {"id": 24, "platform": "快手", "content": "用了半个月说说感受：信号好、电池耐用，干农活拍照也清晰，值！", "likes": 298, "comments": 92, "sentiment": "positive", "ts": "2026-08-02 07:50"},
    {"id": 25, "platform": "快手", "content": "价格比去年涨了不少，配置却没怎么变，先观望再说。", "likes": 121, "comments": 78, "sentiment": "neutral", "ts": "2026-08-02 15:20"},
    {"id": 26, "platform": "快手", "content": "乡镇网点维修方便，摔了一次当天就修好了，服务好评。", "likes": 187, "comments": 49, "sentiment": "positive", "ts": "2026-08-03 12:35"},
    {"id": 27, "platform": "快手", "content": "快充头要另买，标配只有慢充，这点很不厚道。", "likes": 240, "comments": 155, "sentiment": "negative", "ts": "2026-08-04 10:25"},
    {"id": 28, "platform": "快手", "content": "刷到好多评测说法不一，先看看身边人用得咋样再决定。", "likes": 95, "comments": 61, "sentiment": "neutral", "ts": "2026-08-04 18:00"},
]

# 渠道固定顺序，保证统计输出确定性
_PLATFORM_ORDER = ("微博", "小红书", "抖音", "快手")
_SENTIMENT_KEYS = ("positive", "neutral", "negative")


def _engagement(post: dict[str, Any]) -> int:
    """单帖互动量：点赞 + 评论。"""
    return int(post.get("likes", 0)) + int(post.get("comments", 0))


def _pct_shares(counts: dict[str, int]) -> dict[str, float]:
    """计数 → 百分比（0-100）。最大余数法取整，保证各项之和恰为 100。"""
    total = sum(counts.values())
    if total <= 0:
        return {k: 0.0 for k in counts}
    raw = {k: v * 100.0 / total for k, v in counts.items()}
    floors = {k: int(v) for k, v in raw.items()}
    remain = 100 - sum(floors.values())
    for k in sorted(raw, key=lambda x: raw[x] - floors[x], reverse=True)[:remain]:
        floors[k] += 1
    return {k: float(v) for k, v in floors.items()}


def demo_corpus_stats(top_n: int = 5) -> dict[str, Any]:
    """对演示数据源做真实统计（非硬编码），供各 Agent 与 ForumEngine 聚合复用。

    同一批数据只算一次口径，保证不同 query 命中的数字一致、可信：
    - total_posts：帖子总数
    - sentiment_breakdown：整体情绪占比 {positive/neutral/negative}（和为 100）
    - channel_stats：每渠道一条 {channel, posts, positive_pct, neutral_pct,
      negative_pct, engagement}
    - channel_volume：每渠道一条 {channel, posts, engagement}（渠道声量）
    - top_posts：按互动量降序前 top_n 条 {platform, content, likes, comments, sentiment}
    - spread：{total_likes, hot_posts}，hot_posts = 互动量高于全体均值的帖子数
    """
    posts = _DEMO_POSTS
    total = len(posts)

    overall_counts: dict[str, int] = {k: 0 for k in _SENTIMENT_KEYS}
    by_channel: dict[str, list[dict[str, Any]]] = {}
    for post in posts:
        overall_counts[post["sentiment"]] = overall_counts.get(post["sentiment"], 0) + 1
        by_channel.setdefault(post["platform"], []).append(post)

    # 固定渠道优先、其余渠道兜底（防御未来新增平台），空渠道不输出
    channels = (
        [p for p in _PLATFORM_ORDER if by_channel.get(p)]
        + sorted(c for c in by_channel if c not in _PLATFORM_ORDER)
    )

    channel_stats: list[dict[str, Any]] = []
    channel_volume: list[dict[str, Any]] = []
    for ch in channels:
        items = by_channel[ch]
        counts = {k: sum(1 for it in items if it["sentiment"] == k) for k in _SENTIMENT_KEYS}
        shares = _pct_shares(counts)
        engagement = sum(_engagement(it) for it in items)
        channel_stats.append(
            {
                "channel": ch,
                "posts": len(items),
                "positive_pct": shares["positive"],
                "neutral_pct": shares["neutral"],
                "negative_pct": shares["negative"],
                "engagement": engagement,
            }
        )
        channel_volume.append({"channel": ch, "posts": len(items), "engagement": engagement})

    top_posts = [
        {
            "platform": p["platform"],
            "content": p["content"],
            "likes": p["likes"],
            "comments": p["comments"],
            "sentiment": p["sentiment"],
        }
        for p in sorted(posts, key=_engagement, reverse=True)[: max(1, min(int(top_n), total))]
    ]

    avg_engagement = sum(_engagement(p) for p in posts) / max(1, total)
    return {
        "total_posts": total,
        "sentiment_breakdown": _pct_shares(overall_counts),
        "channel_stats": channel_stats,
        "channel_volume": channel_volume,
        "top_posts": top_posts,
        "spread": {
            "total_likes": sum(int(p.get("likes", 0)) for p in posts),
            "hot_posts": sum(1 for p in posts if _engagement(p) > avg_engagement),
        },
    }


def _wrap(fn: Any) -> Any:
    async def _run(**kwargs: Any) -> str:
        try:
            result = await fn(**kwargs)
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    _run.__name__ = fn.__name__
    return _run


async def _search_tool(keyword: str = "", limit: int = 5) -> dict[str, Any]:
    """检索工具：按关键词匹配演示数据源，返回命中的帖子。"""
    kw = (keyword or "").strip()
    hits = [
        p for p in _DEMO_POSTS
        if not kw or kw in p["content"] or kw in p["platform"]
    ]
    return {"total": len(hits), "posts": hits[: max(1, min(int(limit), 20))]}


async def _doc_parse_tool(url: str = "", content: str = "") -> dict[str, Any]:
    """文档解析工具：解析 URL / 文本，提取正文与关键词。"""
    if url:
        # 演示：模拟抓取网页并解析
        text = f"【{url}】页面正文：这是一篇关于舆情的示例文章，包含事件描述与网友评论。"
    else:
        text = content or "（无内容）"
    # 简易中文关键词提取：按 2-gram 统计（先剔除标点）
    _punct = "，。！？、；：""''（）《》【】,.!?;:\"'()<>[] \t\n\r"
    cleaned = text.translate(str.maketrans("", "", _punct))
    grams: dict[str, int] = {}
    for i in range(max(0, len(cleaned) - 1)):
        g = cleaned[i : i + 2]
        grams[g] = grams.get(g, 0) + 1
    keywords = sorted(grams, key=grams.get, reverse=True)[:8]
    return {"url": url, "text": text[:500], "keywords": keywords}


async def _db_query_tool(table: str = "posts", condition: str = "") -> dict[str, Any]:
    """数据库查询工具：查询演示数据源（对应 MySQL 舆情落库表）。"""
    rows = _DEMO_POSTS
    if condition:
        rows = [p for p in rows if condition in json.dumps(p, ensure_ascii=False)]
    return {"table": table, "rows": rows[:10], "count": len(rows)}


async def _sentiment_tool(text: str = "") -> dict[str, Any]:
    """情感分析工具：基于词表的轻量情感打分（-1 ~ 1）。"""
    pos_words = ["好评", "满意", "不错", "快", "好", "五星", "解决", "颜值", "性价比", "续航", "喜欢"]
    neg_words = ["差评", "差", "贵", "涨", "慢", "不理", "差劲", "问题", "等了一小时", "重"]
    pos = sum(1 for w in pos_words if w in text)
    neg = sum(1 for w in neg_words if w in text)
    score = (pos - neg) / max(1, pos + neg)
    if score > 0.2:
        label = "正面"
    elif score < -0.2:
        label = "负面"
    else:
        label = "中性"
    return {"text": text[:200], "score": round(score, 3), "label": label}


class ToolRegistry:
    """工具注册中心：注册 4 类 Function Calling 工具供 Agent 使用。"""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register(self, name: str, description: str, schema: dict, fn: Any) -> None:
        self._tools[name] = {
            "description": description,
            "parameters": schema,
            "fn": _wrap(fn),
        }

    def specs(self) -> list[dict[str, Any]]:
        return [
            {"name": n, "description": t["description"], "parameters": t["parameters"]}
            for n, t in self._tools.items()
        ]

    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> Any | None:
        tool = self._tools.get(name)
        return tool["fn"] if tool else None


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        "search_posts",
        "检索多平台舆情帖子，按关键词过滤，返回命中的帖子列表。",
        {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "limit": {"type": "integer", "description": "返回条数，默认 5"},
            },
            "required": [],
        },
        _search_tool,
    )
    reg.register(
        "parse_document",
        "解析网页/文本内容，提取正文与关键词。",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "网页地址"},
                "content": {"type": "string", "description": "文本内容"},
            },
            "required": [],
        },
        _doc_parse_tool,
    )
    reg.register(
        "query_db",
        "查询舆情数据库（帖子表），支持按条件过滤。",
        {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "表名，默认 posts"},
                "condition": {"type": "string", "description": "过滤条件字符串"},
            },
            "required": [],
        },
        _db_query_tool,
    )
    reg.register(
        "sentiment_analysis",
        "对一段文本进行情感分析，返回情感标签与分数。",
        {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "待分析文本"},
            },
            "required": ["text"],
        },
        _sentiment_tool,
    )
    return reg
