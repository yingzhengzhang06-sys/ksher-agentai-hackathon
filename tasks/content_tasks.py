"""
内容生成 Celery 任务

生成朋友圈、海报、案例文章等内容。
"""
import logging

from celery import shared_task
from datetime import datetime
from models.workflow_models import ContentState
from services.material_service import save_material, update_lifecycle_state, get_current_week
from agents.content_agent import ContentAgent
from agents.design_agent import DesignAgent
from agents.knowledge_agent import KnowledgeAgent
from services.llm_client import LLMClient
from services.knowledge_loader import KnowledgeLoader

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="tasks.generate_morning_briefing")
def generate_morning_briefing(self) -> dict:
    """
    生成晨间情报简报（06:00 执行后）。

    Returns:
        {"success": bool, "content": str, "error": str}
    """
    logger.info("[Celery] 生成晨间情报简报")
    try:
        # 调用 KnowledgeAgent 生成简报
        llm_client = LLMClient()
        knowledge_loader = KnowledgeLoader()
        agent = KnowledgeAgent(llm_client, knowledge_loader)
        result = agent.generate({
            "task": "morning_briefing",
            "date": "today",
        })

        return {"success": True, "content": result.get("content", ""), "error": ""}
    except Exception as e:
        logger.exception("[Celery] 简报生成失败")
        return {"success": False, "content": "", "error": str(e)}


@shared_task(bind=True, name="tasks.generate_daily_content")
def generate_daily_content(self, theme: str, platform: str = "wechat_moments") -> dict:
    """
    生成当日内容（朋友圈/海报）。

    Returns:
        {"success": bool, "material_id": str, "error": str}
    """
    logger.info(f"[Celery] 生成内容: {theme} @ {platform}")

    try:
        llm_client = LLMClient()
        knowledge_loader = KnowledgeLoader()
        content_agent = ContentAgent(llm_client, knowledge_loader)

        # 生成文案
        context = {
            "task": "generate_content",
            "theme": theme,
            "platform": platform,
            "industry": "b2c",
            "target_country": "thailand",
        }
        content_result = content_agent.generate(context)

        # 生成海报设计建议
        design_agent = DesignAgent(llm_client, knowledge_loader)
        design_result = design_agent.generate({
            "task": "poster_design",
            "theme": theme,
            "content": content_result.get("content", ""),
        })

        # 保存素材
        week_year, week_number = get_current_week()
        day_of_week = (datetime.now().weekday() + 1) % 7 or 1  # 周一=1

        from services.material_service import generate_material_id, get_week_dates
        dates = get_week_dates(week_year, week_number)
        publish_date = dates[day_of_week - 1] if day_of_week <= len(dates) else dates[-1]

        material_id = generate_material_id(week_year, week_number, day_of_week)
        save_material(
            material_id=material_id,
            week_year=week_year,
            week_number=week_number,
            day_of_week=day_of_week,
            publish_date=publish_date,
            theme=theme,
            title=f"{theme} - {platform}",
            copy_text=content_result.get("content", ""),
            copy_short=content_result.get("short_copy", ""),
            lifecycle_state=ContentState.REVIEW.value,
        )

        # 自动提交审核队列
        update_lifecycle_state(material_id, ContentState.REVIEW.value, triggered_by="celery_task")

        logger.info(f"[Celery] 内容生成完成: {material_id}")
        return {"success": True, "material_id": material_id, "error": ""}
    except Exception as e:
        logger.exception("[Celery] 内容生成失败")
        return {"success": False, "material_id": "", "error": str(e)}


@shared_task(bind=True, name="tasks.analyze_content_performance")
def analyze_content_performance(self, days: int = 7) -> dict:
    """
    分析已发布内容的性能。

    Returns:
        {"success": bool, "insights": list, "error": str}
    """
    logger.info(f"[Celery] 分析内容性能（{days} 天）")
    try:
        # TODO: 实际性能分析逻辑
        # 1. 从 content_schedule 获取已发布内容
        # 2. 从 engagement 数据源收集指标
        # 3. 生成洞察并存储到记忆系统

        insights = []
        return {"success": True, "insights": insights, "error": ""}
    except Exception as e:
        logger.exception("[Celery] 性能分析失败")
        return {"success": False, "insights": [], "error": str(e)}
