"""
FastAPI 入口 — 提供外部触发和状态查询 API

路由：
- POST /api/workflows/trigger/{workflow_id} - 手动触发工作流
- GET /api/workflows/status/{execution_id} - 查询执行状态
- GET /api/workflows/list - 列出工作流
- GET /api/scheduler/jobs - 列出定时任务
- POST /api/scheduler/trigger/{job_id} - 手动触发定时任务
"""
from datetime import datetime
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from core.scheduler import get_scheduler
from core.state_manager import get_execution, list_executions, get_pending_schedules
from core.workflow_engine import WorkflowEngine
from core.workflow_definitions.marketing_daily import register_all_marketing_workflows
from models.moments_models import (
    ErrorCode,
    GenerationStatus,
    MomentsError,
    MomentsFeedbackRequest,
    MomentsFeedbackResponse,
    MomentsGenerateRequest,
    MomentsGenerateResponse,
)
from services.moments_persistence import MomentsPersistence
from services.moments_service import (
    generate_moments_with_ai_callable,
    generate_moments_with_llm_client,
    generate_moments_with_mock,
)
from tasks.workflow_tasks import execute_daily_workflow, execute_weekly_workflow

MOMENTS_RATE_LIMIT_MAX_REQUESTS = 1
MOMENTS_RATE_LIMIT_WINDOW_SECONDS = 10

app = FastAPI(
    title="Ksher Digital Employee API",
    description="市场专员数字员工 API",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Request Models ==========

class TriggerWorkflowRequest(BaseModel):
    workflow_id: str
    triggered_by: str = "api"
    context: Optional[dict] = None


class TriggerJobRequest(BaseModel):
    job_id: str


def _moments_error_response(
    *,
    code: ErrorCode,
    message: str,
    field: Optional[str] = None,
    status: GenerationStatus = GenerationStatus.ERROR,
    http_status: int = 400,
) -> JSONResponse:
    response = MomentsGenerateResponse(
        success=False,
        status=status,
        errors=[
            MomentsError(
                code=code,
                field=field,
                message=message,
            )
        ],
    )
    return JSONResponse(
        status_code=http_status,
        content=response.model_dump(mode="json"),
    )


def _validation_error_to_moments_response(exc: ValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    loc = first_error.get("loc") or []
    field = str(loc[-1]) if loc else None
    error_type = first_error.get("type", "")
    message = str(first_error.get("msg") or "请求参数不合法")

    if error_type == "missing":
        code = ErrorCode.INPUT_EMPTY
        status = GenerationStatus.INPUT_EMPTY
    elif field == "extra_context" and "too_long" in error_type:
        code = ErrorCode.INPUT_TOO_LONG
        status = GenerationStatus.INPUT_TOO_LONG
    else:
        code = ErrorCode.INVALID_OPTION
        status = GenerationStatus.ERROR

    return _moments_error_response(
        code=code,
        message=message,
        field=field,
        status=status,
        http_status=400,
    )


def _select_moments_mock_scenario(extra_context: str) -> str:
    """测试期通过补充说明中的 mock 标记选择固定场景。"""
    marker = (extra_context or "").lower()
    for scenario in ("success", "error", "empty", "sensitive"):
        if f"mock:{scenario}" in marker:
            return scenario
    return "success"


def _has_moments_mock_marker(extra_context: str) -> bool:
    """判断请求是否显式要求固定 Mock 场景。"""
    marker = (extra_context or "").lower()
    return any(f"mock:{scenario}" in marker for scenario in ("success", "error", "empty", "sensitive"))


def _use_real_moments_ai(extra_context: str) -> bool:
    """默认调用真实 AI；显式 mock 模式或 mock 标记用于 QA 稳定复现。"""
    mode = os.getenv("MOMENTS_AI_MODE", "real").strip().lower()
    return mode != "mock" and not _has_moments_mock_marker(extra_context)


def get_moments_llm_client():
    """懒加载现有 LLM client，默认 Mock 模式不会触发密钥读取或网络调用。"""
    from services.llm_client import LLMClient

    return LLMClient()


def _missing_required_moments_field(payload: dict) -> Optional[str]:
    for field in ("content_type", "target_customer", "product_points", "copy_style"):
        value = payload.get(field)
        if value is None or value == "":
            return field
        if field == "product_points" and not value:
            return field
    return None


def get_moments_persistence() -> MomentsPersistence:
    """获取 moments 持久化实例。测试可 monkeypatch 此函数隔离数据库。"""
    return MomentsPersistence()


def _persist_generation_safely(
    request: MomentsGenerateRequest,
    response: MomentsGenerateResponse,
) -> None:
    """持久化失败不影响生成结果展示。"""
    try:
        get_moments_persistence().save_generation(request, response)
    except Exception:
        # MVP 阶段避免因日志失败阻断主链路。后续可接入统一 logger。
        pass


def _is_moments_rate_limited_safely(request: MomentsGenerateRequest) -> bool:
    """同一 session 短时间重复生成时做保守限频，检查失败不阻断主链路。"""
    if not request.session_id:
        return False
    try:
        return get_moments_persistence().is_rate_limited(
            session_id=request.session_id,
            max_requests=MOMENTS_RATE_LIMIT_MAX_REQUESTS,
            window_seconds=MOMENTS_RATE_LIMIT_WINDOW_SECONDS,
        )
    except Exception:
        # 限频依赖本地持久化，持久化不可用时不影响 MVP 生成主链路。
        return False


# ========== Routes ==========

@app.get("/")
def root():
    """API 健康检查"""
    return {
        "status": "ok",
        "service": "Ksher Digital Employee API",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/workflows")
def list_workflows():
    """列出所有已注册的工作流"""
    engine = WorkflowEngine()
    register_all_marketing_workflows(engine)
    workflows = [
        {
            "workflow_id": wf.workflow_id,
            "name": wf.name,
            "description": wf.description,
            "schedule": wf.schedule,
            "enabled": wf.enabled,
            "steps": len(wf.steps),
        }
        for wf in engine.list_workflows()
    ]
    return {"workflows": workflows}


@app.post("/api/workflows/trigger")
def trigger_workflow(request: TriggerWorkflowRequest, background_tasks: BackgroundTasks):
    """手动触发工作流（异步）"""
    if request.workflow_id == "marketing_daily":
        task = execute_daily_workflow.delay(triggered_by=request.triggered_by)
    elif request.workflow_id in ("marketing_weekly", "marketing_weekly_review"):
        task = execute_weekly_workflow.delay(workflow_id=request.workflow_id, triggered_by=request.triggered_by)
    else:
        raise HTTPException(status_code=404, detail=f"未知工作流: {request.workflow_id}")

    return {
        "success": True,
        "message": "工作流已触发",
        "workflow_id": request.workflow_id,
        "task_id": task.id,
        "execution_id": task.result,  # Celery AsyncResult.result 在 complete 后可用
    }


@app.get("/api/workflows/executions/{execution_id}")
def get_workflow_execution(execution_id: str):
    """查询工作流执行状态"""
    exec_record = get_execution(execution_id)
    if not exec_record:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    from core.state_manager import get_step_executions
    steps = get_step_executions(execution_id)

    return {
        "execution_id": execution_id,
        "workflow_id": exec_record["workflow_id"],
        "status": exec_record["status"],
        "triggered_by": exec_record["triggered_by"],
        "started_at": exec_record["started_at"],
        "completed_at": exec_record["completed_at"],
        "error_message": exec_record["error_message"],
        "steps": steps,
        "metadata": exec_record.get("metadata", {}),
    }


@app.get("/api/workflows/executions")
def list_executions_endpoint(workflow_id: Optional[str] = None, limit: int = 50):
    """列出工作流执行记录"""
    return {"executions": list_executions(workflow_id=workflow_id, limit=limit)}


@app.get("/api/scheduler/jobs")
def list_scheduler_jobs():
    """列出定时任务"""
    scheduler = get_scheduler()
    return {"jobs": scheduler.get_scheduled_jobs()}


@app.post("/api/scheduler/trigger")
def trigger_scheduler_job(request: TriggerJobRequest):
    """立即手动触发定时任务"""
    scheduler = get_scheduler()
    result = scheduler.trigger_job_now(request.job_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, "message": f"任务 {request.job_id} 已触发"}


@app.get("/api/content/pending-approvals")
def get_pending_approvals(limit: int = 50):
    """获取待审批内容列表"""
    from services.material_service import get_pending_approvals
    return {"approvals": get_pending_approvals(limit=limit)}


@app.get("/api/content/pending-schedules")
def get_pending_schedules_endpoint(limit: int = 50):
    """获取待发布内容（已到发布时间）"""
    schedules = get_pending_schedules(limit=limit)
    return {"schedules": schedules}


@app.post("/api/moments/generate", response_model=MomentsGenerateResponse)
def generate_moments(payload: dict = Body(...)):
    """生成朋友圈文案草稿（Mock 优先，不调用真实 LLM）。"""
    missing_field = _missing_required_moments_field(payload)
    if missing_field:
        return _moments_error_response(
            code=ErrorCode.INPUT_EMPTY,
            message="必填字段不能为空",
            field=missing_field,
            status=GenerationStatus.INPUT_EMPTY,
            http_status=400,
        )

    try:
        request = MomentsGenerateRequest(**payload)
    except ValidationError as exc:
        return _validation_error_to_moments_response(exc)

    if _is_moments_rate_limited_safely(request):
        return _moments_error_response(
            code=ErrorCode.UNKNOWN_ERROR,
            message="生成请求过于频繁，请稍后再试",
            field="session_id",
            status=GenerationStatus.ERROR,
            http_status=429,
        )

    if _use_real_moments_ai(request.extra_context):
        try:
            response = generate_moments_with_llm_client(
                request,
                get_moments_llm_client(),
            )
        except Exception as exc:
            def failed_ai_call(_system_prompt: str, _user_prompt: str) -> str:
                raise RuntimeError(str(exc))

            response = generate_moments_with_ai_callable(
                request,
                failed_ai_call,
                max_retries=0,
            )
    else:
        scenario = _select_moments_mock_scenario(request.extra_context)
        response = generate_moments_with_mock(request, scenario=scenario)
    _persist_generation_safely(request, response)
    return response


@app.post("/api/moments/feedback", response_model=MomentsFeedbackResponse)
def submit_moments_feedback(request: MomentsFeedbackRequest):
    """提交生成结果反馈。"""
    feedback_id = get_moments_persistence().save_feedback(request)
    return MomentsFeedbackResponse(
        success=True,
        feedback_id=feedback_id,
        message="已收到反馈",
    )


@app.get("/api/moments/generations/{generation_id}")
def get_moments_generation(generation_id: str):
    """查询单条 moments 生成记录，供调试和 QA 使用。"""
    record = get_moments_persistence().get_generation(generation_id)
    if not record:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    return {"success": True, "record": record}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
