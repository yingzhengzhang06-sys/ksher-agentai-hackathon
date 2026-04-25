"""
审批队列端到端测试 — Week 4 验证

验证项：
1. 生成内容 → 进入审批队列
2. 批准 → approved 状态
3. 拒绝 → 返回 draft 状态
4. 安排发布 → 创建 content_schedule
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.material_service import (
    save_material,
    get_pending_approvals,
    approve_material,
    reject_material,
    schedule_material,
    list_schedules_by_material,
    create_content_schedule,
    update_schedule_status,
    init_materials_db,
    init_content_schedule_db,
    get_material,
    update_lifecycle_state,
)


@pytest.fixture(autouse=True)
def clean_dbs():
    """清理数据库"""
    materials_db = os.path.join(os.path.dirname(__file__), "..", "data", "materials.db")
    if os.path.exists(materials_db):
        os.remove(materials_db)
    init_materials_db()
    init_content_schedule_db()
    yield


class TestApprovalQueueE2E:
    def test_generate_to_approval_queue(self):
        """生成内容 → 进入审批队列"""
        save_material(
            material_id="2026-W17-1",
            week_year=2026,
            week_number=17,
            day_of_week=1,
            publish_date="2026-04-27",
            theme="测试主题",
            title="测试标题",
            copy_text="测试文案内容",
            lifecycle_state="review",  # 直接设为 review 状态
        )

        pending = get_pending_approvals()
        assert len(pending) == 1
        assert pending[0]["material_id"] == "2026-W17-1"
        assert pending[0]["lifecycle_state"] == "review"

    def test_approve_flow(self):
        """批准流程：review → approved"""
        save_material(
            material_id="2026-W17-2",
            week_year=2026,
            week_number=17,
            day_of_week=2,
            publish_date="2026-04-28",
            theme="主题2",
            title="标题2",
            copy_text="文案2",
            lifecycle_state="review",
        )

        # 批准
        result = approve_material("2026-W17-2")
        assert result["success"] is True

        # 验证状态
        mat = get_material("2026-W17-2")
        assert mat["lifecycle_state"] == "approved"

        # 审批队列应空
        pending = get_pending_approvals()
        assert len(pending) == 0

    def test_reject_flow(self):
        """拒绝流程：review → draft"""
        save_material(
            material_id="2026-W17-3",
            week_year=2026,
            week_number=17,
            day_of_week=3,
            publish_date="2026-04-29",
            theme="主题3",
            title="标题3",
            copy_text="文案3",
            lifecycle_state="review",
        )

        # 拒绝
        result = reject_material("2026-W17-3", reason="需要修改")
        assert result["success"] is True

        # 验证状态
        mat = get_material("2026-W17-3")
        assert mat["lifecycle_state"] == "draft"

    def test_schedule_publish(self):
        """安排发布：approved → scheduled + content_schedule"""
        save_material(
            material_id="2026-W17-4",
            week_year=2026,
            week_number=17,
            day_of_week=4,
            publish_date="2026-04-30",
            theme="主题4",
            title="标题4",
            copy_text="文案4",
            lifecycle_state="approved",
        )

        # 安排发布（更新状态 + 创建计划）
        schedule_result = schedule_material("2026-W17-4", "wechat_moments", "2026-04-30T10:00:00")
        assert schedule_result["success"] is True

        # 创建发布计划
        schedule_result = create_content_schedule("2026-W17-4", "wechat_moments", "2026-04-30T10:00:00")
        assert schedule_result["success"] is True

        # 验证 lifecycle_state
        mat = get_material("2026-W17-4")
        assert mat["lifecycle_state"] == "scheduled"

        # 验证 content_schedule
        schedules = list_schedules_by_material("2026-W17-4")
        assert len(schedules) == 1
        assert schedules[0]["platform"] == "wechat_moments"

    def test_full_lifecycle(self):
        """完整生命周期：draft → review → approved → scheduled → published"""
        # 1. 生成（draft）
        save_material(
            material_id="2026-W17-5",
            week_year=2026,
            week_number=17,
            day_of_week=5,
            publish_date="2026-05-01",
            theme="完整流程测试",
            title="完整流程标题",
            copy_text="完整流程文案",
            lifecycle_state="draft",
        )

        # 2. 提交审核
        update_lifecycle_state("2026-W17-5", "review", triggered_by="test")
        assert len(get_pending_approvals()) == 1

        # 3. 批准
        approve_material("2026-W17-5")
        mat = get_material("2026-W17-5")
        assert mat["lifecycle_state"] == "approved"

        # 4. 安排发布
        schedule_material("2026-W17-5", "wechat_moments", "2026-05-01T10:00:00")
        create_content_schedule("2026-W17-5", "wechat_moments", "2026-05-01T10:00:00")
        mat = get_material("2026-W17-5")
        assert mat["lifecycle_state"] == "scheduled"

        # 5. 标记发布
        schedules = list_schedules_by_material("2026-W17-5")
        update_schedule_status(schedules[0]["id"], "published", "2026-05-01T10:05:00")

        schedules = list_schedules_by_material("2026-W17-5")
        assert schedules[0]["status"] == "published"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
