"""
学习闭环 — 每周学习循环：收集 performance → 分析模式 → 更新 prompts

核心功能：
1. 每周自动执行学习循环
2. 分析内容性能，提取有效模式
3. 更新 ContentAgent 的 System Prompt
4. 记录学习历史
"""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.performance_analyzer import PerformanceAnalyzer, get_performance_analyzer

logger = logging.getLogger(__name__)


@dataclass
class LearningRecord:
    """学习记录"""
    cycle_id: str
    start_date: str
    end_date: str
    total_contents_analyzed: int
    insights_count: int
    patterns_learned: List[Dict[str, Any]]
    prompt_updates: List[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class LearningLoop:
    """
    学习闭环管理器。

    每周执行一次学习循环：
    1. 收集本周内容性能数据
    2. 分析识别有效模式
    3. 更新 ContentAgent 的 System Prompt
    4. 记录学习历史
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.analyzer = get_performance_analyzer()
        self._learning_history: List[LearningRecord] = []
        self._patterns_file = Path("data/learned_patterns.json")

        # 确保目录存在
        self._patterns_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载历史模式
        self._load_patterns()

    def _load_patterns(self):
        """加载历史学习模式"""
        if self._patterns_file.exists():
            try:
                with open(self._patterns_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._learning_history = [
                        LearningRecord(**record) for record in data.get("history", [])
                    ]
                logger.info(f"[LearningLoop] 加载了 {len(self._learning_history)} 条学习历史")
            except Exception as e:
                logger.warning(f"[LearningLoop] 加载历史模式失败: {e}")
                self._learning_history = []

    def _save_patterns(self):
        """保存学习模式"""
        try:
            data = {
                "history": [
                    {
                        "cycle_id": r.cycle_id,
                        "start_date": r.start_date,
                        "end_date": r.end_date,
                        "total_contents_analyzed": r.total_contents_analyzed,
                        "insights_count": r.insights_count,
                        "patterns_learned": r.patterns_learned,
                        "prompt_updates": r.prompt_updates,
                        "created_at": r.created_at,
                    }
                    for r in self._learning_history
                ],
                "updated_at": datetime.now().isoformat(),
            }
            with open(self._patterns_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("[LearningLoop] 学习历史已保存")
        except Exception as e:
            logger.error(f"[LearningLoop] 保存学习历史失败: {e}")

    async def run_weekly_cycle(self) -> LearningRecord:
        """
        执行每周学习循环。

        Returns:
            学习记录
        """
        logger.info("[LearningLoop] 开始执行每周学习循环")

        # 1. 确定本周时间范围（上周六到本周五）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # 2. 收集本周内容性能数据
        performances = self._collect_weekly_performance(start_date, end_date)

        # 3. 分析性能，生成洞察
        insights = self.analyzer.generate_insights(performances)

        # 4. 提取学习模式
        patterns = self.analyzer.get_learned_patterns()

        # 5. 更新 ContentAgent 的 System Prompt
        prompt_updates = self._update_content_agent_prompt(patterns, insights)

        # 6. 创建学习记录
        record = LearningRecord(
            cycle_id=self._generate_cycle_id(),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_contents_analyzed=len(performances),
            insights_count=len(insights),
            patterns_learned=patterns,
            prompt_updates=prompt_updates,
        )

        # 7. 保存学习历史
        self._learning_history.append(record)
        self._save_patterns()

        logger.info(
            f"[LearningLoop] 学习循环完成: 分析了 {len(performances)} 条内容，"
            f"提取了 {len(patterns)} 个模式"
        )

        return record

    def _collect_weekly_performance(
        self, start_date: datetime, end_date: datetime
    ) -> List:
        """
        收集指定时间段的内容性能数据。

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            性能数据列表
        """
        # TODO: 从数据库或 analytics_collector 加载性能数据
        # 这里先返回空列表，实际实现需要从 content_performance 表读取
        performances = self.analyzer.load_performance_data(days=7)
        return performances

    def _update_content_agent_prompt(
        self, patterns: List[Dict[str, Any]], insights: List
    ) -> List[str]:
        """
        更新 ContentAgent 的 System Prompt。

        Args:
            patterns: 学习到的模式
            insights: 性能洞察

        Returns:
            更新描述列表
        """
        updates = []

        # 生成学习模式提示
        if patterns:
            pattern_text = self._format_patterns_for_prompt(patterns)
            updates.append(f"注入学习模式: {pattern_text[:50]}...")

            # 保存到文件供 ContentAgent 读取
            self._save_prompt_patterns(pattern_text)

        # 生成洞察提示
        if insights:
            insight_text = self._format_insights_for_prompt(insights)
            updates.append(f"注入性能洞察: {len(insights)} 条")

        return updates

    def _format_patterns_for_prompt(self, patterns: List[Dict[str, Any]]) -> str:
        """
        将学习模式格式化为可注入 Prompt 的文本。

        Args:
            patterns: 模式列表

        Returns:
            格式化的文本
        """
        if not patterns:
            return "暂无学习到的高绩效模式。"

        lines = [
            "## 基于历史数据学习到的高绩效内容模式",
            "以下模式来自对过去一周高绩效内容的分析，生成内容时请参考：",
            ""
        ]

        for pattern in patterns:
            freq = pattern.get("frequency", 0) * 100
            lines.append(
                f"- **{pattern.get('type', '未知')}**: {pattern.get('description', '')} "
                f"(出现频率 {freq:.1f}%)"
            )

        return "\n".join(lines)

    def _format_insights_for_prompt(self, insights: List) -> str:
        """
        将性能洞察格式化为可注入 Prompt 的文本。

        Args:
            insights: 洞察列表

        Returns:
            格式化的文本
        """
        if not insights:
            return ""

        lines = ["## 内容性能洞察", ""]

        for insight in insights:
            lines.append(f"- {insight.description}")

        return "\n".join(lines)

    def _save_prompt_patterns(self, text: str):
        """
        保存学习模式到文件，供 ContentAgent 读取。

        Args:
            text: 学习模式文本
        """
        patterns_file = Path("data/learned_patterns_prompt.txt")
        try:
            with open(patterns_file, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"[LearningLoop] 学习模式已保存到 {patterns_file}")
        except Exception as e:
            logger.error(f"[LearningLoop] 保存学习模式失败: {e}")

    def get_current_patterns(self) -> str:
        """
        获取当前学习到的模式（用于注入到 ContentAgent）。

        Returns:
            格式化的模式文本
        """
        patterns_file = Path("data/learned_patterns_prompt.txt")
        if patterns_file.exists():
            try:
                with open(patterns_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"[LearningLoop] 读取学习模式失败: {e}")

        # 如果没有文件，从历史记录生成
        if self._learning_history:
            latest = self._learning_history[-1]
            return self._format_patterns_for_prompt(latest.patterns_learned)

        return "暂无学习到的高绩效模式。"

    def _generate_cycle_id(self) -> str:
        """生成学习循环 ID"""
        now = datetime.now()
        return now.strftime("learning_cycle_%Y%m%d_%H%M%S")

    def get_learning_summary(self, cycles: int = 5) -> Dict[str, Any]:
        """
        获取学习摘要。

        Args:
            cycles: 最近多少个周期

        Returns:
            学习摘要
        """
        recent = self._learning_history[-cycles:] if cycles > 0 else self._learning_history

        if not recent:
            return {
                "total_cycles": 0,
                "total_contents_analyzed": 0,
                "total_patterns_learned": 0,
            }

        return {
            "total_cycles": len(self._learning_history),
            "recent_cycles": len(recent),
            "total_contents_analyzed": sum(
                r.total_contents_analyzed for r in recent
            ),
            "total_patterns_learned": sum(
                len(r.patterns_learned) for r in recent
            ),
            "last_cycle": (
                {
                    "cycle_id": recent[-1].cycle_id,
                    "date": recent[-1].end_date,
                    "patterns": len(recent[-1].patterns_learned),
                }
                if recent
                else None
            ),
        }

    def get_patterns_for_agent(self, agent_name: str) -> str:
        """
        获取特定 Agent 的学习模式。

        Args:
            agent_name: Agent 名称（如 "content"）

        Returns:
            该 Agent 的学习模式文本
        """
        if agent_name == "content":
            return self.get_current_patterns()
        return ""


# 全局学习闭环实例
_global_learning_loop: Optional[LearningLoop] = None


def get_learning_loop() -> LearningLoop:
    """获取全局学习闭环实例（单例）"""
    global _global_learning_loop
    if _global_learning_loop is None:
        _global_learning_loop = LearningLoop()
    return _global_learning_loop
