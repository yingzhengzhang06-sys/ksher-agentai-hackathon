"""
工作流引擎测试 — Week 1 验证

验证项：
1. 内容生命周期状态机：draft → review → approved → scheduled → published → analyzing → archived
2. 状态转换回调触发
3. WorkflowEngine 注册与执行
4. 审批队列端到端
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from models.workflow_models import ContentState, WorkflowStatus, WorkflowStepType
from core.workflow_engine import ContentLifecycle, WorkflowEngine
from core.state_manager import (
    init_workflow_db,
    get_execution,
    get_step_executions,
    get_state_transitions,
    create_execution,
    update_execution_status,
)
from core.event_bus import EventBus
from core.workflow_definitions.marketing_daily import (
    MARKETING_DAILY_WORKFLOW,
    register_all_marketing_workflows,
)
from services import material_service as ms


# ---------- Fixtures ----------

@pytest.fixture(autouse=True)
def clean_dbs():
    """每次测试前清理数据库"""
    # 清理 workflow db
    workflow_db = os.path.join(os.path.dirname(__file__), "..", "data", "workflow.db")
    if os.path.exists(workflow_db):
        os.remove(workflow_db)
    init_workflow_db()

    # 清理 materials db
    materials_db = os.path.join(os.path.dirname(__file__), "..", "data", "materials.db")
    if os.path.exists(materials_db):
        os.remove(materials_db)
    ms.init_materials_db()

    yield


# ---------- ContentLifecycle 状态机测试 ----------

class TestContentLifecycle:
    def test_initial_state_is_draft(self):
        lc = ContentLifecycle(material_id="test-001")
        assert lc.state == ContentState.DRAFT.value

    def test_draft_to_review(self):
        lc = ContentLifecycle(material_id="test-002")
        lc.submit(triggered_by="user")
        assert lc.state == ContentState.REVIEW.value

    def test_review_to_approved(self):
        lc = ContentLifecycle(material_id="test-003", initial_state=ContentState.REVIEW.value)
        lc.approve(triggered_by="admin")
        assert lc.state == ContentState.APPROVED.value

    def test_review_to_draft_reject(self):
        lc = ContentLifecycle(material_id="test-004", initial_state=ContentState.REVIEW.value)
        lc.reject(triggered_by="admin")
        assert lc.state == ContentState.DRAFT.value

    def test_full_lifecycle(self):
        lc = ContentLifecycle(material_id="test-005")
        lc.submit(triggered_by="system")
        lc.approve(triggered_by="admin")
        lc.schedule(triggered_by="system")
        lc.publish(triggered_by="system")
        lc.start_analysis(triggered_by="system")
        lc.archive(triggered_by="system")
        assert lc.state == ContentState.ARCHIVED.value

    def test_invalid_transition_raises(self):
        lc = ContentLifecycle(material_id="test-006")
        with pytest.raises(Exception):  # transitions 会抛 MachineError
            lc.approve(triggered_by="user")

    def test_reset_from_any_state(self):
        lc = ContentLifecycle(material_id="test-007", initial_state=ContentState.SCHEDULED.value)
        lc.reset(triggered_by="admin")
        assert lc.state == ContentState.DRAFT.value

    def test_state_transition_persisted(self):
        material_id = "test-008"
        lc = ContentLifecycle(material_id=material_id)
        lc.submit(triggered_by="system")
        lc.approve(triggered_by="admin")

        transitions = get_state_transitions(material_id)
        assert len(transitions) == 2
        assert transitions[0]["from_state"] == ContentState.DRAFT.value
        assert transitions[0]["to_state"] == ContentState.REVIEW.value
        assert transitions[1]["from_state"] == ContentState.REVIEW.value
        assert transitions[1]["to_state"] == ContentState.APPROVED.value

    def test_event_bus_notification(self):
        events = []
        bus = EventBus()
        bus.subscribe("content.state_changed", lambda p: events.append(p))

        # 手动替换 get_event_bus 返回的实例（monkeypatch）
        import core.workflow_engine as we_module
        original_bus = we_module.get_event_bus
        we_module.get_event_bus = lambda: bus

        try:
            lc = ContentLifecycle(material_id="test-009")
            lc.submit(triggered_by="system")
            assert len(events) == 1
            assert events[0]["material_id"] == "test-009"
            assert events[0]["to_state"] == ContentState.REVIEW.value
        finally:
            we_module.get_event_bus = original_bus


# ---------- WorkflowEngine 测试 ----------

class TestWorkflowEngine:
    def test_register_and_get_workflow(self):
        engine = WorkflowEngine()
        engine.register_workflow(MARKETING_DAILY_WORKFLOW)

        wf = engine.get_workflow("marketing_daily")
        assert wf is not None
        assert wf.name == "市场专员日度工作流"
        assert len(wf.steps) == 4

    def test_execute_workflow_with_handlers(self):
        engine = WorkflowEngine()
        register_all_marketing_workflows(engine)

        call_log = []

        def mock_handler(step, context, execution_id):
            call_log.append(step.step_id)
            return {"mock": True}

        engine.register_step_handler(WorkflowStepType.INTELLIGENCE_SCAN.value, mock_handler)
        engine.register_step_handler(WorkflowStepType.CONTENT_GENERATION.value, mock_handler)
        engine.register_step_handler(WorkflowStepType.REVIEW_QUEUE.value, mock_handler)
        engine.register_step_handler(WorkflowStepType.PERFORMANCE_MONITOR.value, mock_handler)

        result = engine.execute_workflow("marketing_daily", triggered_by="test")
        assert result["success"] is True
        assert result["execution_id"] != ""
        assert len(call_log) == 4

        # 验证持久化
        exec_record = get_execution(result["execution_id"])
        assert exec_record["status"] == WorkflowStatus.COMPLETED.value
        assert exec_record["workflow_id"] == "marketing_daily"

        steps = get_step_executions(result["execution_id"])
        assert len(steps) == 4
        assert all(s["status"] == WorkflowStatus.COMPLETED.value for s in steps)

    def test_missing_handler_fails(self):
        engine = WorkflowEngine()
        engine.register_workflow(MARKETING_DAILY_WORKFLOW)
        # 不注册任何 handler

        result = engine.execute_workflow("marketing_daily", triggered_by="test")
        assert result["success"] is False
        assert "未注册处理器" in result["error"]

    def test_disabled_workflow_fails(self):
        engine = WorkflowEngine()
        wf = MARKETING_DAILY_WORKFLOW.model_copy(update={"enabled": False})
        engine.register_workflow(wf)

        result = engine.execute_workflow("marketing_daily", triggered_by="test")
        assert result["success"] is False
        assert "已禁用" in result["error"]

    def test_execute_nonexistent_workflow(self):
        engine = WorkflowEngine()
        result = engine.execute_workflow("not_exist", triggered_by="test")
        assert result["success"] is False
        assert "未找到工作流" in result["error"]


# ---------- 审批队列测试 ----------

class TestApprovalQueue:
    def test_approval_queue_end_to_end(self):
        # 1. 创建素材
        material_id = "2026-W17-1"
        ms.save_material(
            material_id=material_id,
            week_year=2026,
            week_number=17,
            day_of_week=1,
            publish_date="2026-04-27",
            theme="测试主题",
            title="测试标题",
            copy_text="测试文案内容",
            lifecycle_state="review",
        )

        # 2. 查询待审批
        pending = ms.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0]["material_id"] == material_id

        # 3. 审批通过
        result = ms.approve_material(material_id, approved_by="admin")
        assert result["success"] is True

        mat = ms.get_material(material_id)
        assert mat["lifecycle_state"] == "approved"

        # 4. 待审批应为空
        pending = ms.get_pending_approvals()
        assert len(pending) == 0

    def test_reject_returns_to_draft(self):
        material_id = "2026-W17-2"
        ms.save_material(
            material_id=material_id,
            week_year=2026,
            week_number=17,
            day_of_week=2,
            publish_date="2026-04-28",
            theme="测试主题2",
            title="测试标题2",
            copy_text="测试文案内容2",
            lifecycle_state="review",
        )

        ms.reject_material(material_id, reason="需要修改", rejected_by="admin")
        mat = ms.get_material(material_id)
        assert mat["lifecycle_state"] == "draft"

    def test_content_schedule(self):
        material_id = "2026-W17-3"
        ms.save_material(
            material_id=material_id,
            week_year=2026,
            week_number=17,
            day_of_week=3,
            publish_date="2026-04-29",
            theme="测试主题3",
            title="测试标题3",
            copy_text="测试文案内容3",
            lifecycle_state="approved",
        )

        # 创建发布计划
        result = ms.create_content_schedule(
            material_id=material_id,
            platform="wechat_moments",
            scheduled_at="2026-04-29T10:00:00",
        )
        assert result["success"] is True
        assert result["id"] > 0

        # 查询计划
        schedules = ms.list_schedules_by_material(material_id)
        assert len(schedules) == 1
        assert schedules[0]["platform"] == "wechat_moments"

    def test_get_materials_by_lifecycle_state(self):
        for i, state in enumerate(["draft", "review", "approved", "published"]):
            ms.save_material(
                material_id=f"2026-W17-{i+10}",
                week_year=2026,
                week_number=17,
                day_of_week=i + 1,
                publish_date="2026-04-27",
                theme=f"主题{i}",
                title=f"标题{i}",
                copy_text=f"文案{i}",
                lifecycle_state=state,
            )

        approved = ms.get_materials_by_lifecycle_state("approved")
        assert len(approved) == 1
        assert approved[0]["lifecycle_state"] == "approved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
