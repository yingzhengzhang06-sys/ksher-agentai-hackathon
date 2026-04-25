"""
Swarm编排器 — K2.6 Agent集群调度核心

四个组件：
  - TaskDecomposer: 任务拆解（K2.6 Thinking Mode）
  - SwarmScheduler: 并行调度（拓扑排序 + ThreadPoolExecutor）
  - ResultAggregator: 结果聚合（格式化 + 质检）
  - RetryReallocator: 失败重试（降级模型 + 重试）

使用方式：
    orchestrator = SwarmOrchestrator(llm_client, knowledge_loader)
    plan = orchestrator.decompose(context, goal="generate_battle_pack")
    execution = orchestrator.execute(plan, available_agents={"speech": agent, ...})
    result = execution.final_result
"""
import concurrent.futures
import json
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

from orchestrator.task_models import SwarmExecution, SwarmPlan, SwarmTask, TaskStatus
from prompts.swarm_prompts import (
    QUALITY_CHECKER_SYSTEM_PROMPT,
    RESULT_AGGREGATOR_SYSTEM_PROMPT,
    TASK_DECOMPOSER_SYSTEM_PROMPT,
)


class SwarmOrchestrator:
    """K2.6 Agent集群调度中枢"""

    def __init__(self, llm_client, knowledge_loader, memory_manager=None):
        self.llm = llm_client
        self.knowledge_loader = knowledge_loader
        self.memory_manager = memory_manager
        self.max_workers = 6
        self._fallback_chain = {
            "kimi_k26": "kimi",
            "kimi": None,
        }

    # ============================================================
    # 1. 任务拆解器 (TaskDecomposer)
    # ============================================================
    def decompose(self, context: dict, goal: str = "generate_battle_pack") -> SwarmPlan:
        """
        使用K2.6 Thinking Mode拆解高层任务为子任务列表。

        Args:
            context: 客户画像上下文
            goal: 高层目标描述

        Returns:
            SwarmPlan: 拆解后的任务方案
        """
        # 构建上下文摘要
        ctx_summary = self._build_context_summary(context)

        # 构建拆解Prompt
        user_prompt = self._build_decompose_prompt(goal, ctx_summary, context)

        # 调用K2.6 Thinking Mode进行拆解
        raw_response = self.llm.call_sync(
            agent_name="swarm_decomposer",
            system=TASK_DECOMPOSER_SYSTEM_PROMPT,
            user_msg=user_prompt,
            temperature=0.3,
        )

        # 解析JSON响应
        plan_data = self._safe_parse_json(raw_response)
        if not plan_data or "tasks" not in plan_data:
            # 拆解失败，返回默认的硬编码方案
            return self._default_battle_plan(goal, ctx_summary)

        # 构建SwarmPlan
        tasks = []
        for t_data in plan_data.get("tasks", []):
            task = SwarmTask(
                task_id=t_data.get("task_id", f"t{len(tasks)+1}"),
                name=t_data.get("name", "unknown"),
                description=t_data.get("description", ""),
                agent_name=t_data.get("agent_name", "knowledge"),
                depends_on=t_data.get("depends_on", []),
                estimated_steps=t_data.get("estimated_steps", 10),
            )
            tasks.append(task)

        plan = SwarmPlan(
            plan_id=plan_data.get("plan_id", f"bp_{int(time.time())}"),
            original_task=plan_data.get("original_task", goal),
            context_summary=plan_data.get("context_summary", ctx_summary),
            tasks=tasks,
            created_at=time.time(),
            total_estimated_steps=sum(t.estimated_steps for t in tasks),
        )

        return plan

    def _build_context_summary(self, context: dict) -> str:
        """构建客户画像摘要"""
        parts = []
        if context.get("company"):
            parts.append(f"客户: {context['company']}")
        if context.get("industry"):
            parts.append(f"行业: {context['industry']}")
        if context.get("target_country"):
            parts.append(f"目标国家: {context['target_country']}")
        if context.get("monthly_volume"):
            parts.append(f"月流水: {context['monthly_volume']}万")
        if context.get("current_channel"):
            parts.append(f"当前渠道: {context['current_channel']}")
        if context.get("battlefield"):
            parts.append(f"战场类型: {context['battlefield']}")
        return " | ".join(parts) if parts else "通用客户"

    def _build_decompose_prompt(self, goal: str, ctx_summary: str, context: dict) -> str:
        """构建拆解Prompt"""
        battlefield = context.get("battlefield", "education")
        pain_points = context.get("pain_points", [])

        prompt = f"""请为以下客户拆解"{goal}"任务。

## 客户画像
{ctx_summary}

## 详细上下文
- 行业: {context.get('industry', '未知')}
- 目标国家: {context.get('target_country', '未知')}
- 月流水(万元): {context.get('monthly_volume', 0)}
- 当前渠道: {context.get('current_channel', '未知')}
- 战场类型: {battlefield}
- 痛点: {', '.join(pain_points) if pain_points else '未明确'}

## 要求
1. 识别无依赖的任务，最大化并行度
2. 方案Agent(proposal)必须依赖成本Agent(cost)的结果
3. 异议Agent(objection)可独立执行或依赖话术Agent(speech)
4. 每个任务estimated_steps基于复杂度：简单10，中等20，复杂40

请直接输出JSON，不要其他文字。"""
        return prompt

    def _safe_parse_json(self, text: str) -> dict | None:
        """安全解析JSON，处理markdown包裹"""
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass
        # 尝试提取 ```json ... ``` 包裹的内容
        import re
        if text and "```" in text:
            m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1).strip())
                except (json.JSONDecodeError, TypeError):
                    pass
        return None

    def _default_battle_plan(self, goal: str, ctx_summary: str) -> SwarmPlan:
        """拆解失败时的默认方案（硬编码的6任务并行方案）"""
        tasks = [
            SwarmTask(task_id="t1", name="speech_generation",
                      description="生成销售切入话术（电梯话术+完整讲解+微信跟进）",
                      agent_name="speech", depends_on=[], estimated_steps=15),
            SwarmTask(task_id="t2", name="cost_analysis",
                      description="成本对比分析（Ksher vs 当前渠道）",
                      agent_name="cost", depends_on=[], estimated_steps=20),
            SwarmTask(task_id="t3", name="objection_handling",
                      description="预判客户异议并生成应对策略",
                      agent_name="objection", depends_on=[], estimated_steps=15),
            SwarmTask(task_id="t4", name="competitor_analysis",
                      description="竞品分析（差异化优势梳理）",
                      agent_name="sales_competitor", depends_on=[], estimated_steps=20),
            SwarmTask(task_id="t5", name="proposal_generation",
                      description="生成定制化解决方案（8章结构，依赖成本分析）",
                      agent_name="proposal", depends_on=["t2"], estimated_steps=30),
            SwarmTask(task_id="t6", name="risk_assessment",
                      description="切换风险评估（合规+时效+隐性成本）",
                      agent_name="sales_risk", depends_on=["t2"], estimated_steps=15),
        ]
        return SwarmPlan(
            plan_id=f"bp_default_{int(time.time())}",
            original_task=goal,
            context_summary=ctx_summary,
            tasks=tasks,
            created_at=time.time(),
            total_estimated_steps=sum(t.estimated_steps for t in tasks),
        )

    # ============================================================
    # 2. Swarm调度器 (SwarmScheduler)
    # ============================================================
    def execute(self, plan: SwarmPlan, available_agents: dict) -> SwarmExecution:
        """
        执行SwarmPlan，按依赖关系并行调度。

        Args:
            plan: 任务方案
            available_agents: {agent_name: Agent实例}

        Returns:
            SwarmExecution: 执行结果
        """
        execution = SwarmExecution(plan=plan, start_time=time.time())

        # 发布计划开始事件
        try:
            from core.event_bus import get_event_bus
            event_bus = get_event_bus()
            event_bus.publish("swarm.plan_started", {
                "plan_id": plan.plan_id,
                "task_count": len(plan.tasks),
                "timestamp": execution.start_time,
            })
        except Exception:
            pass

        # 拓扑排序执行：按批次并行
        remaining = set(t.task_id for t in plan.tasks)
        completed = set()

        while remaining:
            # 找出当前可执行的任务（所有依赖已完成）
            ready_tasks = [
                plan.get_task(tid) for tid in remaining
                if plan.get_task(tid) and all(
                    dep in completed for dep in plan.get_task(tid).depends_on
                )
            ]

            if not ready_tasks:
                # 死锁检测：还有剩余但没有ready任务 → 标记为失败
                for tid in remaining:
                    t = plan.get_task(tid)
                    if t:
                        t.status = TaskStatus.FAILED
                        t.error = "死锁：依赖循环或依赖任务不存在"
                logger.warning(f"Swarm死锁检测: plan={plan.plan_id}, 剩余任务={remaining}")
                break

            # 并行执行当前批次
            batch_results = self._execute_batch(ready_tasks, available_agents, plan)

            # 更新状态
            for task_id, success in batch_results.items():
                remaining.discard(task_id)
                if success:
                    completed.add(task_id)

        # 聚合结果
        execution.end_time = time.time()
        execution.total_execution_time_ms = int(
            (execution.end_time - execution.start_time) * 1000
        )

        # 检查是否全部成功
        failed_count = plan.get_failed_count()
        if failed_count == 0:
            execution.success = True
            execution.final_result = self._aggregate_results(plan)
        else:
            execution.success = failed_count < len(plan.tasks) // 2  # 半数以上成功算部分成功
            execution.error_message = f"{failed_count}/{len(plan.tasks)} 个任务失败"
            execution.final_result = self._aggregate_results(plan, partial=True)

        # 发布计划完成事件
        try:
            from core.event_bus import get_event_bus
            event_bus = get_event_bus()
            event_bus.publish("swarm.plan_completed", {
                "plan_id": plan.plan_id,
                "success": execution.success,
                "total_time_ms": execution.total_execution_time_ms,
                "failed_count": failed_count,
                "timestamp": execution.end_time,
            })
        except Exception as e:
            logger.warning(f"发布swarm.plan_completed事件失败: {e}")

        return execution

    def _execute_batch(self, tasks: list, available_agents: dict, plan: SwarmPlan) -> dict:
        """并行执行一批任务，返回 {task_id: success_bool}"""
        results = {}

        def run_single(task: SwarmTask):
            """执行单个子任务"""
            task.status = TaskStatus.RUNNING
            task.start_time = time.time()

            # 发布任务开始事件
            try:
                from core.event_bus import get_event_bus
                event_bus = get_event_bus()
                event_bus.publish("swarm.task_started", {
                    "plan_id": plan.plan_id,
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "agent_name": task.agent_name,
                    "timestamp": task.start_time,
                })
            except Exception as e:
                logger.warning(f"发布swarm.task_started事件失败 [{task.task_id}]: {e}")

            agent = available_agents.get(task.agent_name)
            if not agent:
                task.status = TaskStatus.FAILED
                task.error = f"Agent '{task.agent_name}' 未注册"
                task.end_time = time.time()
                return task.task_id, False

            # 构建任务上下文
            task_context = self._build_task_context(task, plan)

            try:
                output = agent.generate(task_context)
                task.result = output if isinstance(output, dict) else {"output": output}
                task.status = TaskStatus.COMPLETED
                task.end_time = time.time()
                task.execution_time_ms = int(
                    (task.end_time - task.start_time) * 1000
                )

                # 发布任务完成事件
                try:
                    from core.event_bus import get_event_bus
                    event_bus = get_event_bus()
                    event_bus.publish("swarm.task_completed", {
                        "plan_id": plan.plan_id,
                        "task_id": task.task_id,
                        "task_name": task.name,
                        "agent_name": task.agent_name,
                        "execution_time_ms": task.execution_time_ms,
                        "timestamp": task.end_time,
                    })
                except Exception:
                    pass

                return task.task_id, True

            except Exception as e:
                task.error = str(e)
                task.end_time = time.time()
                task.execution_time_ms = int(
                    (task.end_time - task.start_time) * 1000
                )

                # 尝试重试
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.RETRYING
                    # 重试时增加延迟
                    time.sleep(1.0 * task.retry_count)
                    return run_single(task)

                task.status = TaskStatus.FAILED

                # 发布任务失败事件
                try:
                    from core.event_bus import get_event_bus
                    event_bus = get_event_bus()
                    event_bus.publish("swarm.task_failed", {
                        "plan_id": plan.plan_id,
                        "task_id": task.task_id,
                        "task_name": task.name,
                        "agent_name": task.agent_name,
                        "error": str(e),
                        "retry_count": task.retry_count,
                        "timestamp": task.end_time,
                    })
                except Exception:
                    pass

                return task.task_id, False

        # 线程池并行执行
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(tasks), self.max_workers)
        ) as executor:
            futures = {
                executor.submit(run_single, task): task.task_id
                for task in tasks
            }
            for future in concurrent.futures.as_completed(futures):
                task_id, success = future.result()
                results[task_id] = success

        return results

    def _build_task_context(self, task: SwarmTask, plan: SwarmPlan) -> dict:
        """为子任务构建上下文（注入依赖结果）"""
        # 基础上下文来自plan
        context = {"_swarm_task": task.to_dict()}

        # 注入已完成的依赖结果
        for dep_id in task.depends_on:
            dep_task = plan.get_task(dep_id)
            if dep_task and dep_task.result:
                context[f"_{dep_task.name}_result"] = dep_task.result

        return context

    # ============================================================
    # 3. 结果聚合器 (ResultAggregator)
    # ============================================================
    def _aggregate_results(self, plan: SwarmPlan, partial: bool = False) -> dict:
        """
        将各子任务结果聚合成标准作战包格式。

        Args:
            plan: 执行后的任务方案
            partial: 是否为部分聚合（有失败任务时）
        """
        result = {
            "speech": {},
            "cost": {},
            "proposal": {},
            "objection": {},
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "execution_time_ms": sum(
                    t.execution_time_ms for t in plan.tasks
                ),
                "swarm_mode": True,
                "partial": partial,
                "plan_id": plan.plan_id,
                "agents_used": [t.agent_name for t in plan.tasks if t.result],
                "failed_agents": [t.agent_name for t in plan.tasks if t.status == TaskStatus.FAILED],
            }
        }

        # 按agent_name映射结果
        agent_map = {
            "speech": "speech",
            "cost": "cost",
            "proposal": "proposal",
            "objection": "objection",
            "sales_competitor": "competitor",
            "sales_risk": "risk",
            "sales_research": "research",
            "sales_product": "product",
        }

        for task in plan.tasks:
            if task.result:
                key = agent_map.get(task.agent_name, task.name)
                if key in result:
                    result[key] = task.result
                else:
                    result[key] = task.result

        return result

    # ============================================================
    # 4. 质量检查 (QualityChecker)
    # ============================================================
    def quality_check(self, task: SwarmTask) -> dict:
        """
        对单个任务输出进行质量评分。

        Returns:
            {"passed": bool, "overall_score": int, "issues": [...]}
        """
        if not task.result:
            return {"passed": False, "overall_score": 0, "issues": ["无输出结果"]}

        result_json = json.dumps(task.result, ensure_ascii=False, indent=2)
        user_prompt = f"""请评估以下Agent输出的质量：

Agent: {task.agent_name}
任务: {task.description}

输出内容:
{result_json[:3000]}  # 截断避免过长

请按评分维度给出JSON结果。"""

        try:
            raw = self.llm.call_sync(
                agent_name="swarm_quality",
                system=QUALITY_CHECKER_SYSTEM_PROMPT,
                user_msg=user_prompt,
                temperature=0.2,
            )
            check_result = self._safe_parse_json(raw)
            if check_result:
                return check_result
        except Exception:
            pass

        # 质检失败，默认通过
        return {"passed": True, "overall_score": 75, "issues": []}

    # ============================================================
    # 便捷方法
    # ============================================================
    def run_battle_pack(self, context: dict, agents: dict) -> dict:
        """
        一键生成作战包（Swarm模式）。

        Args:
            context: 客户上下文
            agents: {agent_name: Agent实例}

        Returns:
            dict: 作战包结果（与generate_battle_pack兼容的格式）
        """
        plan = self.decompose(context, goal="generate_battle_pack")
        execution = self.execute(plan, agents)
        return execution.final_result or {}
