"""
晨报生成器 — 销售支持数字员工的每日晨报
自动汇总：汇率/政策/竞品动态 + 昨日数据 + 今日建议
"""
import os
import sys

# 确保能导入项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from services.vector_store import search_knowledge
from services.push_channel import PushMessage, get_push_manager


@dataclass
class BriefingSection:
    """晨报章节"""
    title: str
    content: str
    level: str = "info"  # info / warning / danger


class MorningBriefingGenerator:
    """
    晨报生成器
    每日自动采集多源数据，生成结构化晨报
    """

    # 关注的货币对
    WATCHED_PAIRS = [
        ("USD", "CNY", "美元/人民币"),
        ("THB", "CNY", "泰铢/人民币"),
        ("MYR", "CNY", "马币/人民币"),
        ("PHP", "CNY", "比索/人民币"),
        ("IDR", "CNY", "印尼盾/人民币"),
        ("VND", "CNY", "越南盾/人民币"),
    ]

    # 汇率波动预警阈值
    ALERT_THRESHOLD = 0.005  # 0.5%

    def __init__(self):
        self.sections: List[BriefingSection] = []
        self.push_manager = get_push_manager()

    def _get_exchange_rates(self) -> Dict[str, Any]:
        """
        获取最新汇率（使用exchangerate-api免费版）
        返回各货币对的最新汇率和24小时变化
        """
        try:
            # 使用免费的汇率API（以USD为基础）
            resp = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=10,
            )
            data = resp.json()
            rates = data.get("rates", {})

            result = {}
            for from_code, to_code, label in self.WATCHED_PAIRS:
                usd_to_from = rates.get(from_code, 0)
                usd_to_cny = rates.get("CNY", 0)

                if usd_to_from and usd_to_cny:
                    # 换算: from_code -> CNY
                    rate = usd_to_cny / usd_to_from
                    result[label] = {
                        "rate": round(rate, 6),
                        "from": from_code,
                        "to": to_code,
                    }

            return {
                "date": data.get("date", ""),
                "rates": result,
                "success": True,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "rates": {}}

    def _search_policy_news(self) -> List[Dict[str, str]]:
        """搜索政策新闻（使用Tavily搜索）"""
        try:
            from services.llm_client import _get_secret
            api_key = _get_secret("TAVILY_API_KEY", "")
            if not api_key:
                return []

            queries = [
                "跨境支付政策 外汇管理 最新",
                "东南亚 央行 支付牌照 新规",
                "跨境电商 收款 监管政策",
            ]

            all_results = []
            for query in queries:
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "query": query,
                        "max_results": 3,
                        "search_depth": "basic",
                        "time_range": "day",
                        "api_key": api_key,
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", []):
                        all_results.append({
                            "title": r.get("title", ""),
                            "content": r.get("content", "")[:200],
                            "url": r.get("url", ""),
                        })

            return all_results[:5]  # 最多5条
        except Exception:
            return []

    def _search_competitor_news(self) -> List[Dict[str, str]]:
        """搜索竞品动态"""
        try:
            from services.llm_client import _get_secret
            api_key = _get_secret("TAVILY_API_KEY", "")
            if not api_key:
                return []

            queries = [
                "PingPong 跨境支付 费率 新功能",
                "万里汇 WorldFirst 产品更新",
                "连连国际 跨境收款 动态",
            ]

            all_results = []
            for query in queries:
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "query": query,
                        "max_results": 2,
                        "search_depth": "basic",
                        "time_range": "week",
                        "api_key": api_key,
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", []):
                        all_results.append({
                            "title": r.get("title", ""),
                            "content": r.get("content", "")[:200],
                            "url": r.get("url", ""),
                        })

            return all_results[:5]
        except Exception:
            return []

    def _get_sales_tips(self) -> str:
        """从知识库获取今日销售建议"""
        try:
            # 搜索异议处理和话术相关的知识
            results = search_knowledge("今日销售建议 渠道商", top_k=3)
            if results:
                tips = []
                for r in results:
                    text = r.get("text", "")
                    # 提取"销售要点"部分
                    if "销售要点" in text or "话术" in text:
                        tips.append(text[:200])
                return "\n".join(tips) if tips else "持续关注渠道商需求，主动推送市场动态。"
            return "暂无特定建议。"
        except Exception:
            return "暂无特定建议。"

    def generate(self) -> List[BriefingSection]:
        """生成完整晨报"""
        self.sections = []
        today = datetime.now().strftime("%Y年%m月%d日")

        # 1. 晨报标题
        self.sections.append(BriefingSection(
            title=f"📋 Ksher销售晨报 · {today}",
            content="",
            level="info",
        ))

        # 2. 汇率动态
        rate_data = self._get_exchange_rates()
        if rate_data.get("success"):
            lines = ["### 💱 汇率动态\n"]
            for label, info in rate_data["rates"].items():
                rate = info["rate"]
                lines.append(f"- **{label}**: {rate:.6f}")
            lines.append(f"\n*数据日期: {rate_data.get('date', '今日')}*")
            self.sections.append(BriefingSection(
                title="汇率动态",
                content="\n".join(lines),
                level="info",
            ))

        # 3. 政策/行业动态
        policy_news = self._search_policy_news()
        if policy_news:
            lines = ["### 📰 政策/行业动态\n"]
            for i, news in enumerate(policy_news, 1):
                lines.append(f"{i}. **{news['title']}**")
                lines.append(f"   {news['content']}...")
                lines.append(f"   [详情]({news['url']})")
            self.sections.append(BriefingSection(
                title="政策动态",
                content="\n".join(lines),
                level="info",
            ))

        # 4. 竞品动态
        comp_news = self._search_competitor_news()
        if comp_news:
            lines = ["### 🔍 竞品动态\n"]
            for i, news in enumerate(comp_news, 1):
                lines.append(f"{i}. **{news['title']}**")
                lines.append(f"   {news['content']}...")
            self.sections.append(BriefingSection(
                title="竞品动态",
                content="\n".join(lines),
                level="warning",
            ))

        # 5. 销售建议
        tips = self._get_sales_tips()
        self.sections.append(BriefingSection(
            title="💡 今日销售建议",
            content=f"### 💡 今日销售建议\n\n{tips}",
            level="info",
        ))

        return self.sections

    def to_markdown(self) -> str:
        """将晨报转为Markdown格式"""
        if not self.sections:
            self.generate()

        lines = []
        for section in self.sections:
            if section.title and not section.title.startswith("📋"):
                continue  # 跳过子章节标题（已在content中）
            lines.append(section.content)
            lines.append("\n---\n")

        return "\n".join(lines)

    def to_text(self) -> str:
        """将晨报转为纯文本（适合企微推送）"""
        if not self.sections:
            self.generate()

        lines = []
        for section in self.sections:
            # 移除markdown标记
            content = section.content.replace("### ", "").replace("**", "").replace("- ", "• ")
            lines.append(content)
            lines.append("")

        return "\n".join(lines)

    def push(self, channels: Optional[List[str]] = None) -> Dict[str, dict]:
        """
        推送晨报到指定通道

        Returns:
            {通道名: 推送结果}
        """
        if not self.sections:
            self.generate()

        text_content = self.to_text()
        title = f"Ksher销售晨报 · {datetime.now().strftime('%m月%d日')}"

        msg = PushMessage(
            title=title,
            content=text_content,
            msg_type="text",
        )

        return self.push_manager.push(msg, channels)


def generate_and_push_morning_briefing(channels: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    快捷函数：生成并推送晨报

    用法（作为APScheduler定时任务）:
        from services.morning_briefing import generate_and_push_morning_briefing
        scheduler.add_job(generate_and_push_morning_briefing, 'cron', hour=9, minute=0)
    """
    generator = MorningBriefingGenerator()
    sections = generator.generate()

    result = {
        "generated_at": datetime.now().isoformat(),
        "sections_count": len(sections),
        "sections": [s.title for s in sections],
        "push_results": {},
    }

    # 推送
    push_results = generator.push(channels)
    result["push_results"] = push_results

    return result


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("=" * 60)
    print("MorningBriefingGenerator 测试")
    print("=" * 60)

    gen = MorningBriefingGenerator()
    sections = gen.generate()

    print(f"\n生成 {len(sections)} 个章节:\n")
    for s in sections:
        print(f"[{s.level}] {s.title}")
        print(f"{s.content[:200]}...")
        print()

    print("\n--- 纯文本格式 ---\n")
    print(gen.to_text()[:800])
