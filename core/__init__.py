# Core Modules — 数字员工核心能力

from .decision_engine import MarketingDecisionEngine, get_decision_engine
from .learning_loop import LearningLoop, get_learning_loop
from .performance_analyzer import PerformanceAnalyzer, get_performance_analyzer
from .recommender import ContentRecommender, get_content_recommender
from .workflow_engine import WorkflowEngine
import core.state_manager as state_manager
from .event_bus import EventBus, get_event_bus
from .scheduler import WorkflowScheduler

__all__ = [
    # Decision Engine
    "MarketingDecisionEngine",
    "get_decision_engine",
    # Learning Loop
    "LearningLoop",
    "get_learning_loop",
    # Performance Analyzer
    "PerformanceAnalyzer",
    "get_performance_analyzer",
    # Content Recommender
    "ContentRecommender",
    "get_content_recommender",
    # Workflow Engine
    "WorkflowEngine",
    "state_manager",
    "EventBus",
    "get_event_bus",
    "WorkflowScheduler",
]
