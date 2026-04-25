"""
知识中枢 — 销售支持的数字员工核心能力

基于RAG+Agent架构，提供：
1. 智能问答 - 自然语言查询产品/合规/竞品知识
2. 知识推荐 - 根据客户画像主动推荐知识
3. 记忆系统 - 短期+长期记忆，持续进化

继承自 KnowledgeLoader，增强向量检索能力
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys

# 确保能导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import KNOWLEDGE_DIR, BRAND_COLORS

# 简单的向量检索（基于关键词匹配+TF-IDF风格排序）
# 生产环境应使用 ChromaDB/Milvus 等向量数据库


class KnowledgeHub:
    """
    知识中枢 - 销售支持数字员工的"大脑"

    核心能力：
    1. RAG检索 - 向量+关键词混合检索
    2. 上下文记忆 - 短期记忆（当前对话）+长期记忆（历史经验）
    3. 主动推荐 - 基于客户画像推送相关知识
    4. 学习进化 - 从交互中提取模式，持续优化
    """

    # 知识分类
    KNOWLEDGE_CATEGORIES = {
        "product": "产品知识",
        "compliance": "合规政策",
        "competitor": "竞品分析",
        "case": "成功案例",
        "operation": "操作指南",
        "speech": "话术模板",
    }

    # 客户阶段
    CUSTOMER_STAGES = [
        "潜在客户",
        "初次接触",
        "需求确认",
        "方案沟通",
        "签约中",
        "已签约",
    ]

    def __init__(self, knowledge_dir: Optional[str] = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR

        # 知识库缓存
        self._knowledge_cache: Dict[str, str] = {}

        # 短期记忆（当前客户会话）
        self._short_term_memory: Dict[str, List[dict]] = {}

        # 长期记忆（历史经验）
        self._long_term_memory: List[dict] = []

        # 知识使用统计
        self._usage_stats: Dict[str, int] = {}

    # ==================== 知识加载 ====================

    def load_knowledge(self, category: str, context: dict) -> str:
        """加载指定分类的知识"""
        cache_key = f"{category}_{json.dumps(context, sort_keys=True)}"

        if cache_key in self._knowledge_cache:
            return self._knowledge_cache[cache_key]

        # 根据分类加载知识
        content = self._load_category_content(category, context)

        if content:
            self._knowledge_cache[cache_key] = content
            self._usage_stats[category] = self._usage_stats.get(category, 0) + 1

        return content

    def _load_category_content(self, category: str, context: dict) -> str:
        """按分类加载知识内容"""
        # 产品知识
        if category == "product":
            return self._load_product_knowledge(context)

        # 合规政策
        elif category == "compliance":
            return self._load_compliance_knowledge(context)

        # 竞品分析
        elif category == "competitor":
            return self._load_competitor_knowledge(context)

        # 成功案例
        elif category == "case":
            return self._load_case_knowledge(context)

        # 操作指南
        elif category == "operation":
            return self._load_operation_knowledge(context)

        # 话术模板
        elif category == "speech":
            return self._load_speech_knowledge(context)

        return ""

    def _load_product_knowledge(self, context: dict) -> str:
        """加载产品知识"""
        industry = context.get("industry", "b2c")
        country = context.get("target_country", "")

        knowledge_path = os.path.join(self.knowledge_dir, "products")
        if not os.path.exists(knowledge_path):
            return "产品知识库加载失败"

        # 加载产品信息
        product_info = []
        for root, dirs, files in os.walk(knowledge_path):
            for f in files:
                if f.endswith((".md", ".json")):
                    fp = os.path.join(root, f)
                    try:
                        with open(fp, "r", encoding="utf-8") as file:
                            content = file.read()
                            # 简单过滤：只返回与当前行业/国家相关的内容
                            if industry.lower() in content.lower() or country.lower() in content.lower():
                                product_info.append(content)
                            elif not country:  # 如果没有指定国家，返回通用的
                                product_info.append(content[:500])  # 限制长度
                    except Exception:
                        pass

        return "\n\n---\n\n".join(product_info[:3]) if product_info else "未找到相关产品知识"

    def _load_compliance_knowledge(self, context: dict) -> str:
        """加载合规知识"""
        country = context.get("target_country", "")

        # 基础合规知识
        base_compliance = """
## KYC 开户材料要求

### 货物贸易
- **开户阶段**：公司营业执照、法人身份证、业务证明文件
- **首笔收款**：商业发票(CI) + 报关单(CD)
- **日常收款**：相同品类的贸易单据

### 服务贸易
- **开户阶段**：公司营业执照、法人身份证
- **收款凭证**：合同 + 发票（无需报关单）

### 电商
- **平台交易记录**作为贸易背景证明
- 需提供店铺资质证明
"""

        # 国别合规（简化）
        country_compliance = {
            "thailand": "泰国：需提供税号（Tax ID），支持TMR实时到账",
            "malaysia": "马来西亚：需要公司注册证明（SSM），支持MYR",
            "singapore": "新加坡：持牌机构，需要ACRA证明",
            "indonesia": "印尼：需要NPWP税号，限制某些行业",
        }

        if country.lower() in country_compliance:
            return base_compliance + f"\n\n## {country.title()} 特殊要求\n{country_compliance[country.lower()]}"

        return base_compliance

    def _load_competitor_knowledge(self, context: dict) -> str:
        """加载竞品知识"""
        competitor = context.get("competitor", "")

        if not competitor:
            return "请指定要查询的竞品"

        # 简化竞品数据
        competitors = {
            "pingpong": "优势：知名度高费率透明；弱点：客服响应慢",
            "lianlian": "优势：产品线全；弱点：价格偏高",
            "xtransfer": "优势：B2B专业；弱点：覆盖国家少",
            "airwallex": "优势：技术先进；弱点：费率较高",
        }

        return competitors.get(competitor.lower(), "未找到该竞品信息")

    def _load_case_knowledge(self, context: dict) -> str:
        """加载案例知识"""
        industry = context.get("industry", "")
        country = context.get("target_country", "")

        return f"""
## 成功案例参考

### {industry}行业 - {country or '通用'}案例

**客户画像**：目标年交易额500万-2000万美元的中型企业
**痛点**：原有渠道费率过高、结算周期长
**方案**：推荐Ksher企业版账户 + 多币种钱包
**效果**：费率降低0.3%，结算周期缩短至T+1

**关键成功要素**：
1. 充分了解客户现有成本结构
2. 强调合规安全保障
3. 提供试用体验
"""

    def _load_operation_knowledge(self, context: dict) -> str:
        """加载操作知识"""
        return """
## 常用操作指南

### 开户流程
1. 提交KYC材料（营业执照、法人身份证、业务证明）
2. 初审（1-2工作日）
3. 终审（1-2工作日）
4. 开通账户（收到邮件通知）

### 常见问题
- **开户时间**：3-5工作日
- **费率调整**：联系客户经理申请
- **账户激活**：首笔入账自动激活
"""

    def _load_speech_knowledge(self, context: dict) -> str:
        """加载话术知识"""
        scenario = context.get("scenario", "")

        return f"""
## 销售话术 - {scenario or '通用场景'}

### 开场白
"您好，我是Ksher的小X，专门为跨境企业提供收款解决方案。请问您目前有相关的需求吗？"

### 价值呈现
"我们帮助企业平均降低0.2%的收款成本，最快T+0到账。"

### 异议处理
- **价格高**："我们的费率包含合规保障和本地化服务，综合成本其实更低"
- **考虑下**："好的，您可以先了解下，我们提供免费试用"
"""

    # ==================== RAG检索 ====================

    def query(self, question: str, context: dict) -> dict:
        """
        RAG检索：理解问题 → 检索知识 → 生成回答

        Returns:
            {
                "answer": "回答内容",
                "sources": ["知识来源列表"],
                "confidence": 0.85,  # 置信度
                "suggested_agents": ["speech", "cost"],  # 推荐的Agent
            }
        """
        # 1. 意图识别
        intent = self._recognize_intent(question)

        # 2. 检索相关知识
        relevant_knowledge = self._retrieve_knowledge(question, intent, context)

        # 3. 生成回答（简化版，生产环境应调用LLM）
        answer = self._generate_answer(question, relevant_knowledge, context)

        return {
            "answer": answer,
            "sources": relevant_knowledge.get("sources", []),
            "confidence": relevant_knowledge.get("confidence", 0.5),
            "intent": intent,
            "suggested_agents": self._get_suggested_agents(intent),
        }

    def _recognize_intent(self, question: str) -> str:
        """识别问题意图"""
        question_lower = question.lower()

        # 产品查询
        if any(k in question_lower for k in ["产品", "费率", "支持", "收款", "账户"]):
            return "product"

        # 合规咨询
        if any(k in question_lower for k in ["合规", "KYC", "材料", "开户", "需要什么"]):
            return "compliance"

        # 竞品对比
        if any(k in question_lower for k in ["对比", "比", "优势", "弱点", "vs", "还是"]):
            return "competitor"

        # 案例需求
        if any(k in question_lower for k in ["案例", "成功", "客户", "做过"]):
            return "case"

        # 操作问题
        if any(k in question_lower for k in ["怎么", "如何", "操作", "流程", "步骤"]):
            return "operation"

        # 话术需求
        if any(k in question_lower for k in ["话术", "说", "开场", "异议", "回复"]):
            return "speech"

        return "general"

    def _retrieve_knowledge(self, question: str, intent: str, context: dict) -> dict:
        """检索知识"""
        # 获取相关分类的知识
        knowledge = self.load_knowledge(intent, context)

        # 简单相关性评估
        confidence = 0.7
        if len(knowledge) > 100:
            confidence = 0.85

        return {
            "content": knowledge,
            "sources": [f"knowledge/{intent}/"],
            "confidence": confidence,
        }

    def _generate_answer(self, question: str, knowledge: dict, context: dict) -> str:
        """生成回答（模板+知识，生产环境应调用LLM）"""
        content = knowledge.get("content", "")

        if not content:
            return "抱歉，我没有找到相关的知识。请问可以换个方式描述您的问题吗？"

        # 简单模板回答
        intent = knowledge.get("intent", "general")

        templates = {
            "product": f"根据产品知识库：\n\n{content[:800]}",
            "compliance": f"关于合规要求：\n\n{content[:800]}",
            "speech": f"参考话术：\n\n{content[:800]}",
            "case": f"成功案例参考：\n\n{content[:800]}",
        }

        return templates.get(intent, f"找到相关信息：\n\n{content[:800]}")

    def _get_suggested_agents(self, intent: str) -> List[str]:
        """根据意图推荐Agent"""
        intent_agent_map = {
            "product": ["speech", "cost"],
            "compliance": ["proposal", "speech"],
            "competitor": ["objection", "speech"],
            "case": ["speech", "proposal"],
            "operation": ["knowledge"],
            "speech": ["speech", "objection"],
            "general": ["knowledge"],
        }
        return intent_agent_map.get(intent, ["knowledge"])

    # ==================== 记忆系统 ====================

    def remember_interaction(
        self,
        customer_id: str,
        question: str,
        answer: str,
        agents_used: List[str],
        feedback: Optional[int] = None,
    ):
        """记录交互到记忆系统"""

        # 短期记忆
        if customer_id not in self._short_term_memory:
            self._short_term_memory[customer_id] = []

        self._short_term_memory[customer_id].append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "agents_used": agents_used,
            "feedback": feedback,
        })

        # 如果有正向反馈，记录到长期记忆
        if feedback and feedback >= 4:
            self._long_term_memory.append({
                "question_pattern": question[:100],
                "answer_summary": answer[:200],
                "agents": agents_used,
                "effectiveness": feedback,
                "timestamp": datetime.now().isoformat(),
            })

    def recall_similar(self, question: str, customer_id: str = "") -> Optional[dict]:
        """回忆相似问题的最佳答案"""

        # 先查短期记忆
        if customer_id and customer_id in self._short_term_memory:
            for mem in reversed(self._short_term_memory[customer_id][-5:]):
                if any(k in mem.get("question", "") for k in question.split()[:3]):
                    return mem

        # 再查长期记忆（简化匹配）
        for mem in reversed(self._long_term_memory[-10:]):
            if any(k in mem.get("question_pattern", "") for k in question.split()[:3]):
                return mem

        return None

    # ==================== 主动推荐 ====================

    def suggest_knowledge(self, customer_context: dict) -> List[dict]:
        """根据客户画像推荐相关知识"""
        suggestions = []

        industry = customer_context.get("industry", "")
        country = customer_context.get("target_country", "")
        stage = customer_context.get("stage", "潜在客户")

        # 根据阶段推荐
        stage_recommendations = {
            "潜在客户": ["产品介绍", "成功案例"],
            "初次接触": ["产品对比", "开场话术"],
            "需求确认": ["方案设计", "成本分析"],
            "方案沟通": ["竞品分析", "异议处理"],
            "签约中": ["合规材料", "KYC流程"],
            "已签约": ["使用教程", "增值服务"],
        }

        recommended_topics = stage_recommendations.get(stage, [])

        for topic in recommended_topics:
            suggestions.append({
                "topic": topic,
                "category": self._topic_to_category(topic),
                "reason": f"客户处于【{stage}】阶段，推荐了解",
            })

        return suggestions

    def _topic_to_category(self, topic: str) -> str:
        """话题转分类"""
        mapping = {
            "产品介绍": "product",
            "产品对比": "competitor",
            "成功案例": "case",
            "开场话术": "speech",
            "方案设计": "case",
            "成本分析": "product",
            "竞品分析": "competitor",
            "异议处理": "speech",
            "合规材料": "compliance",
            "KYC流程": "operation",
            "使用教程": "operation",
            "增值服务": "product",
        }
        return mapping.get(topic, "product")

    # ==================== 统计分析 ====================

    def get_stats(self) -> dict:
        """获取知识使用统计"""
        return {
            "usage_by_category": self._usage_stats,
            "total_queries": sum(self._usage_stats.values()),
            "long_term_memory_count": len(self._long_term_memory),
            "short_term_customers": len(self._short_term_memory),
        }

    def get_popular_knowledge(self, limit: int = 5) -> List[dict]:
        """获取热门知识排行"""
        sorted_stats = sorted(
            self._usage_stats.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [
            {"category": cat, "count": count, "name": self.KNOWLEDGE_CATEGORIES.get(cat, cat)}
            for cat, count in sorted_stats[:limit]
        ]


# 单例实例
_knowledge_hub_instance = None


def get_knowledge_hub() -> KnowledgeHub:
    """获取知识中枢单例"""
    global _knowledge_hub_instance
    if _knowledge_hub_instance is None:
        _knowledge_hub_instance = KnowledgeHub()
    return _knowledge_hub_instance