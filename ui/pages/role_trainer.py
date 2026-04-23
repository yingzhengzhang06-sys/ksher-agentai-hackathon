"""
话术培训师 — AI陪练中心

5个Tab：新人带教 / 话术练兵 / 异议攻防 / 实战模拟 / 考核中心
核心转变：从"看答案"到"先练再对照"的训练模式
AI评分：LLM优先，Mock降级为关键词匹配

V4增强：
- Tab1 AI智能学习建议
- Tab2 AI教练深度点评（心理学框架+技巧分析）
- Tab3 AI动态异议生成+多角色挑战
- Tab4 对话阶段追踪+客户情绪系统+2新角色
- Tab5 技能雷达图+AI训练报告
- 训练数据持久化
"""

import json
import os
import glob
import re
import random
import time
import uuid
from datetime import date, datetime

import streamlit as st
import plotly.graph_objects as go

from config import BRAND_COLORS, BATTLEFIELD_TYPES, DATA_DIR, TYPE_SCALE, SPACING, RADIUS
from ui.components.ui_cards import hex_to_rgb, render_kpi_card, render_status_badge, render_border_item, render_score_card, render_flex_row
from prompts.trainer_prompts import (
    ADVISOR_SYSTEM_PROMPT, ADVISOR_USER_TEMPLATE,
    COACH_SYSTEM_PROMPT, COACH_USER_TEMPLATE,
    OBJECTION_GEN_SYSTEM_PROMPT, OBJECTION_GEN_USER_TEMPLATE,
    ENHANCED_SIMULATION_SYSTEM_PROMPT_TEMPLATE,
    REPORTER_SYSTEM_PROMPT, REPORTER_USER_TEMPLATE,
)


# ============================================================
# 通用工具函数
# ============================================================

def _is_mock_mode() -> bool:
    """判断是否为 mock 模式"""
    return not st.session_state.get("battle_router_ready", False)


def _get_llm():
    """获取 LLM 客户端"""
    return st.session_state.get("llm_client")


def _llm_score(system_prompt: str, user_msg: str, agent_name: str = "objection") -> str:
    """调用 LLM 进行评分，失败返回空字符串"""
    llm = _get_llm()
    if not llm:
        return ""
    try:
        return llm.call_sync(agent_name=agent_name, system=system_prompt,
                             user_msg=user_msg, temperature=0.3)
    except Exception:
        return ""


def _llm_chat(system_prompt: str, messages: list, agent_name: str = "speech") -> str:
    """调用 LLM 进行多轮对话，失败返回空字符串"""
    llm = _get_llm()
    if not llm:
        return ""
    try:
        return llm.call_with_history(agent_name=agent_name, system=system_prompt,
                                     messages=messages, temperature=0.7)
    except Exception:
        return ""


def _parse_json_score(text: str) -> dict | None:
    """从 LLM 返回文本中提取 JSON 评分"""
    try:
        # 尝试直接解析
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # 尝试从 markdown 代码块提取
    if text and "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                return json.loads(block)
            except (json.JSONDecodeError, TypeError):
                continue
    return None



# ============================================================
# 训练数据持久化
# ============================================================

def _get_training_data_path() -> str:
    """获取训练数据存储目录"""
    path = os.path.join(DATA_DIR, "feedback", "training")
    os.makedirs(path, exist_ok=True)
    return path


def _save_training_result(result_type: str, result: dict):
    """保存训练结果到磁盘（跨会话持久化）"""
    try:
        path = _get_training_data_path()
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{result_type}.json"
        filepath = os.path.join(path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "type": result_type,
                "timestamp": datetime.now().isoformat(),
                "data": result,
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 持久化失败不阻塞主流程


def _load_training_history(result_type: str = None, limit: int = 50) -> list:
    """读取训练历史记录"""
    path = _get_training_data_path()
    if not os.path.exists(path):
        return []
    files = sorted(glob.glob(os.path.join(path, "*.json")), reverse=True)
    results = []
    for f in files[:limit * 3]:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if result_type is None or data.get("type") == result_type:
                    results.append(data)
                    if len(results) >= limit:
                        break
        except (json.JSONDecodeError, IOError):
            continue
    return results


def _parse_sim_metadata(reply: str) -> tuple:
    """解析增强模拟回复中的META元数据"""
    match = re.search(r'<!-- META: ({.*?}) -->', reply)
    if match:
        try:
            meta = json.loads(match.group(1))
            clean_text = re.sub(r'\s*<!-- META:.*?-->\s*', '', reply).strip()
            return clean_text, meta
        except json.JSONDecodeError:
            pass
    return reply, {}


def _mock_stage_emotion(messages: list) -> dict:
    """Mock模式下根据对话轮次和关键词推断阶段和情绪"""
    user_msgs = [m for m in messages if m["role"] == "user"]
    n = len(user_msgs)
    stages = ["开场寒暄", "需求挖掘", "产品推荐", "异议处理", "促成签约"]
    stage = stages[min(n, len(stages) - 1)]

    last_user = user_msgs[-1]["content"] if user_msgs else ""
    if any(kw in last_user for kw in ["价格", "贵", "便宜", "费率高"]):
        emotion = "怀疑"
    elif any(kw in last_user for kw in ["试用", "开户", "合作", "可以"]):
        emotion = "感兴趣"
    elif any(kw in last_user for kw in ["不需要", "再说", "算了"]):
        emotion = "不耐烦"
    elif any(kw in last_user for kw in ["牌照", "安全", "合规"]):
        emotion = "中性"
    else:
        emotion = "中性"
    return {"stage": stage, "emotion": emotion}


# ============================================================
# 评分 System Prompt 模板
# ============================================================

SCORING_SYSTEM_PROMPT = """你是一位资深的跨境支付销售培训师，专门评估销售人员的话术质量。

请根据以下4个维度对销售人员的回答进行评分（每项0-10分），并给出具体的改进建议。

评分维度：
1. 说服力：是否抓住客户痛点，是否有吸引力
2. 专业度：产品知识是否准确（费率/牌照/时效等）
3. 完整度：是否覆盖关键要素（费率/时效/牌照/下一步行动）
4. 合规性：是否有合规风险的表述（不能承诺收益、不能虚假宣传）

请严格按照以下JSON格式返回，不要包含其他内容：
```json
{
  "persuasion": 7,
  "expertise": 8,
  "completeness": 6,
  "compliance": 9,
  "total": 30,
  "comment": "整体不错，但缺少下一步行动号召...",
  "improvements": ["建议加入具体数字增强说服力", "需要提到本地牌照优势"]
}
```"""

OBJECTION_SCORING_PROMPT = """你是一位资深的跨境支付销售培训师，专门评估销售人员应对客户异议的能力。

请根据以下4个维度对销售人员的异议回应进行评分（每项0-10分）：
1. 说服力：回应是否能有效化解客户异议
2. 专业度：是否用了准确的数据和事实
3. 完整度：是否既化解异议又推进了下一步
4. 合规性：是否有合规风险

同时，请将用户的回答与3种标准回应策略进行对比分析。

请严格按照以下JSON格式返回：
```json
{
  "persuasion": 7,
  "expertise": 8,
  "completeness": 6,
  "compliance": 9,
  "total": 30,
  "strategy_match": "共情型",
  "comment": "你的回应偏向共情策略，效果不错...",
  "improvements": ["可以补充具体数据增强说服力", "建议加入行动号召"]
}
```"""

SIMULATION_SYSTEM_PROMPT_TEMPLATE = """你现在扮演一位{customer_type}的客户，正在考虑跨境收款方案。

你的角色设定：
- 公司：{company}
- 行业：{industry}
- 现有收款渠道：{current_channel}
- 月流水：{volume}万元
- 痛点：{pain_points}
- 性格特点：{personality}

对话规则：
1. 你是客户，不是销售。始终从客户角度说话
2. 根据你的性格特点，适当提出异议和质疑
3. 如果销售说得好，可以逐步表现出兴趣
4. 如果销售说得不好，表现出不耐烦或质疑
5. 对话控制在5-8轮左右，之后自然结束
6. 每次回复控制在2-3句话

当用户发送"[结束对话]"时，请按以下JSON格式给出评分：
```json
{{
  "opening": 7,
  "needs_discovery": 8,
  "product_match": 6,
  "objection_handling": 7,
  "closing": 5,
  "total": 33,
  "comment": "整体表现...",
  "highlights": ["做得好的地方1", "做得好的地方2"],
  "improvements": ["需要改进的地方1", "需要改进的地方2"]
}}
```"""

SIMULATION_SCORING_PROMPT = """你是一位资深的跨境支付销售培训师。请对以下销售对话进行评估。

评分维度（每项0-10分）：
1. 开场（opening）：是否快速建立信任
2. 需求挖掘（needs_discovery）：是否了解客户痛点
3. 产品推荐（product_match）：方案是否匹配需求
4. 异议处理（objection_handling）：应对异议是否有效
5. 促成签约（closing）：是否有效推进下一步

请严格按照以下JSON格式返回：
```json
{
  "opening": 7,
  "needs_discovery": 8,
  "product_match": 6,
  "objection_handling": 7,
  "closing": 5,
  "total": 33,
  "comment": "整体表现...",
  "highlights": ["做得好的地方1"],
  "improvements": ["需要改进的地方1"]
}
```"""


# ============================================================
# 数据结构
# ============================================================

# ---- 新人带教：30天入职计划 ----
ONBOARDING_PLAN = {
    "week1": {
        "title": "Week 1: 产品与合规基础",
        "theme": "了解 Ksher 是谁、做什么、怎么合规",
        "objectives": [
            "掌握 Ksher 三大产品线（B2B/B2C/服务贸易）",
            "理解费率体系和阶梯定价",
            "了解 KYC/AML 合规基础",
            "熟悉东南亚8国支付牌照布局",
            "能独立介绍 Ksher 核心优势",
        ],
        "courses": [
            {"name": "Ksher 产品线总览", "type": "必修", "duration": "30min"},
            {"name": "B2B 跨境收款产品详解", "type": "必修", "duration": "45min"},
            {"name": "B2C 电商收款方案", "type": "必修", "duration": "30min"},
            {"name": "服务贸易收款（6大场景）", "type": "必修", "duration": "45min"},
            {"name": "费率体系与阶梯定价", "type": "必修", "duration": "30min"},
            {"name": "KYC/AML 合规基础", "type": "必修", "duration": "30min"},
            {"name": "东南亚8国牌照与监管", "type": "选修", "duration": "20min"},
        ],
        "practice": "完成「话术练兵 → 场景示范」中「首次接触」场景学习",
        "exam": "产品知识测试（考核中心），≥80分通关",
    },
    "week2": {
        "title": "Week 2: 销售流程与话术",
        "theme": "学会说 Ksher 的语言",
        "objectives": [
            "掌握3种战场策略（增量/存量/教育）",
            "背诵5个核心话术场景",
            "了解 CRM 客户管理流程",
            "能根据客户类型选择对应战场策略",
        ],
        "courses": [
            {"name": "三大战场策略详解", "type": "必修", "duration": "45min"},
            {"name": "增量战场：从银行抢客户", "type": "必修", "duration": "30min"},
            {"name": "存量战场：从竞品抢客户", "type": "必修", "duration": "30min"},
            {"name": "教育战场：新客户培育", "type": "必修", "duration": "30min"},
            {"name": "5大核心话术场景", "type": "必修", "duration": "45min"},
            {"name": "CRM 客户管理流程", "type": "必修", "duration": "20min"},
        ],
        "practice": "完成「话术练兵」所有5个场景的填空练习，每个≥24分",
        "exam": "话术背诵通关（考核中心 → 话术实操）",
    },
    "week3": {
        "title": "Week 3: 异议处理与竞品",
        "theme": "面对客户质疑不慌张",
        "objectives": [
            "掌握6类常见异议+3种回应策略",
            "了解12个主要竞品的优劣势",
            "能针对不同竞品给出差异化话术",
            "初步具备独立处理客户异议的能力",
        ],
        "courses": [
            {"name": "6类常见异议解析", "type": "必修", "duration": "45min"},
            {"name": "3种回应策略（直接/共情/数据）", "type": "必修", "duration": "30min"},
            {"name": "竞品概览（12家）", "type": "必修", "duration": "45min"},
            {"name": "Ksher vs 银行 对比话术", "type": "必修", "duration": "20min"},
            {"name": "Ksher vs PingPong/万里汇 话术", "type": "必修", "duration": "20min"},
            {"name": "Ksher vs 空中云汇/连连 话术", "type": "选修", "duration": "20min"},
        ],
        "practice": "完成「异议攻防」初级+中级训练，平均分≥24分",
        "exam": "异议模拟通关（考核中心 → 异议处理考核），≥24分",
    },
    "week4": {
        "title": "Week 4: 实战带训",
        "theme": "在实战中检验所学",
        "objectives": [
            "完成至少2次实战模拟（不同客户类型）",
            "跟随老员工完成1次真实客户拜访",
            "独立完成1次客户首次接触",
            "通过综合实操考核",
        ],
        "courses": [
            {"name": "实战模拟：价格敏感型客户", "type": "必修", "duration": "30min"},
            {"name": "实战模拟：品牌忠诚型客户", "type": "必修", "duration": "30min"},
            {"name": "销售全流程复盘", "type": "必修", "duration": "45min"},
            {"name": "签约流程与注意事项", "type": "选修", "duration": "20min"},
        ],
        "practice": "完成「实战模拟」至少2个不同客户类型，每个≥35分",
        "exam": "综合实操评分（考核中心 → 综合考核），≥70分",
    },
}

# ---- 话术练兵：场景数据 ----
SPEECH_SCENES = {
    "首次接触": {
        "description": "第一次联系潜在客户，建立信任并引起兴趣",
        "standard_script": (
            "您好，我是Ksher的XX。Ksher是专注东南亚跨境收款的支付公司，"
            "持有8国本地牌照，本地直连清算，到账快、费率透明。"
            "很多做东南亚的中国企业都在用我们。"
        ),
        "key_points": ["8国本地牌照", "本地直连清算", "到账快", "费率透明", "0元开户"],
        "tips": "首次接触重点是建立信任+引起兴趣，不要急于报价",
        "practice_scenario": "客户是做泰国B2B出口的贸易公司，月流水约80万，目前用银行电汇收款。你在展会上第一次接触到对方负责人。",
    },
    "费率谈判": {
        "description": "客户询问费率，需要清晰报价并体现价值",
        "standard_script": (
            "我们的费率结构很透明：手续费+汇兑佣金分开报价，没有隐藏费用。"
            "底价0.05%起，根据月流水量阶梯定价。"
            "您月流水XX万的话，综合成本大约在0.6%-0.8%。"
        ),
        "key_points": ["费率透明", "手续费+汇兑佣金分开", "阶梯定价", "综合成本概念", "无隐藏费用"],
        "tips": "报价时要引导客户关注「综合成本」而非「表面费率」",
        "practice_scenario": "客户是做B2C电商的，月流水200万，目前用PingPong，觉得费率还行。他问你：'你们费率多少？'",
    },
    "竞品对比": {
        "description": "客户提到正在用竞品或在对比，需要差异化定位",
        "standard_script": (
            "和XX相比，我们最大的差异是东南亚本地牌照直连清算——"
            "不走中间行，到账更快，汇率更优。"
            "很多从XX转过来的客户反馈，光汇率差这一项每月就省了好几千。"
        ),
        "key_points": ["本地牌照直连", "不走中间行", "到账更快", "汇率更优", "客户案例佐证"],
        "tips": "不要贬低竞品，聚焦Ksher的独特价值（东南亚本地牌照）",
        "practice_scenario": "客户正在用万里汇，月流水150万，做东南亚B2B。他说：'万里汇用着还行，你们有什么不一样的？'",
    },
    "促成签约": {
        "description": "客户已有兴趣，需要推动下一步行动",
        "standard_script": (
            "基于您的情况，我建议先开一个免费账户试用。"
            "0元开户、0月费，先跑一笔小额感受一下到账速度和汇率。"
            "满意了再逐步切量，没有任何风险。"
        ),
        "key_points": ["0元开户", "0月费", "小额试用", "先感受", "逐步切量", "无风险"],
        "tips": "降低门槛是关键——0成本试用消除犹豫",
        "practice_scenario": "客户了解了你们的方案，表示有兴趣但还没下定决心。他说：'方案听起来不错，我再考虑考虑。'",
    },
    "客户犹豫": {
        "description": "客户表示需要考虑/回去商量，需要保持联系",
        "standard_script": (
            "理解您的顾虑。很多客户刚开始也有同样的想法，"
            "后来试了一笔之后就转过来了。"
            "要不这样，我给您安排一个7天的体验期，您先感受一下？"
        ),
        "key_points": ["理解顾虑", "社会证明", "降低门槛", "限时体验", "保持联系"],
        "tips": "不要施压，用「理解+案例+低门槛方案」组合拳",
        "practice_scenario": "客户说：'我需要回去和老板商量一下，回头再联系你吧。' 这通常意味着客户不太确定，你需要保持住沟通。",
    },
    "合规解释": {
        "description": "客户问到合规、牌照、资金安全等问题",
        "standard_script": (
            "这是非常好的问题。Ksher 持有香港MSO牌照、泰国BOT支付牌照等8国本地牌照。"
            "客户资金由花旗、汇丰等国际银行独立托管，与公司运营资金完全隔离。"
            "我们通过了PCI DSS安全认证，所有交易都有完整的KYC/AML审核。"
        ),
        "key_points": ["8国本地牌照", "资金银行托管", "账户隔离", "PCI DSS认证", "KYC/AML合规"],
        "tips": "合规问题要正面回答，用具体牌照名称和银行名称增强可信度",
        "practice_scenario": "客户是做跨境电商的，之前听说过某支付公司出了资金问题。他问：'你们的资金安全吗？有什么保障？'",
    },
}

# ---- 异议攻防：扩展异议数据（含难度分级）----
EXTENDED_OBJECTIONS = {
    "初级": [
        {
            "objection": "没听过 Ksher，你们靠谱吗？",
            "context": "银行客户对 Ksher 品牌认知度低",
            "battlefield": "increment",
            "key_elements": ["牌照", "投资方", "客户数", "资金托管"],
        },
        {
            "objection": "费率看起来和别人差不多",
            "context": "客户单纯比较表面费率",
            "battlefield": "stock",
            "key_elements": ["综合成本", "锁汇", "到账速度", "本地客服"],
        },
        {
            "objection": "量不大，暂时不需要",
            "context": "新客户觉得业务规模小",
            "battlefield": "education",
            "key_elements": ["0门槛", "早建立合规通道", "隐性成本"],
        },
    ],
    "中级": [
        {
            "objection": "我要回去和老板商量一下",
            "context": "客户没有决策权或在推脱",
            "battlefield": "education",
            "key_elements": ["了解决策链", "提供书面方案", "约定回访时间"],
        },
        {
            "objection": "能再便宜点吗？已经在跟你们竞品谈了",
            "context": "客户用竞品压价",
            "battlefield": "stock",
            "key_elements": ["价值而非价格", "差异化服务", "综合成本"],
        },
        {
            "objection": "换渠道太麻烦了，现在也能用",
            "context": "客户对切换成本有顾虑",
            "battlefield": "increment",
            "key_elements": ["迁移支持", "并行运行", "时间成本计算"],
        },
    ],
    "高级": [
        {
            "objection": "听说你们在越南有合规问题？",
            "context": "客户听到负面信息",
            "battlefield": "stock",
            "key_elements": ["正面回应", "具体牌照", "第三方验证", "客户案例"],
        },
        {
            "objection": "上次用你们的服务，到账延迟了3天，怎么解释？",
            "context": "客户有过不好的体验",
            "battlefield": "stock",
            "key_elements": ["致歉", "原因分析", "改进措施", "补偿方案"],
        },
        {
            "objection": "我们做欧美市场为主，东南亚只是很小一部分，没必要单独接一个渠道",
            "context": "东南亚非核心市场",
            "battlefield": "education",
            "key_elements": ["东南亚增长潜力", "多渠道并行", "0成本接入"],
        },
    ],
}

# ---- 实战模拟：客户角色 ----
CUSTOMER_PERSONAS = {
    "价格敏感型": {
        "company": "深圳优品贸易有限公司",
        "industry": "B2B货贸",
        "current_channel": "银行电汇",
        "volume": "80",
        "pain_points": "手续费太高、到账太慢",
        "personality": "精打细算，任何费用都要问清楚。对价格极其敏感，会反复比价。说话直接，不喜欢绕弯子。",
        "opening": "你好，我是优品贸易的采购总监王明。听说你们做跨境收款的？费率多少？直接说。",
        "difficulty": "简单",
    },
    "品牌忠诚型": {
        "company": "广州跨洋科技有限公司",
        "industry": "B2C电商",
        "current_channel": "PingPong",
        "volume": "200",
        "pain_points": "东南亚市场收款不方便，到账慢",
        "personality": "对现有供应商有感情，不轻易换。需要充分的理由才会考虑。比较理性，会用数据说话。",
        "opening": "嗯，你好。我们一直用PingPong，用了快3年了，合作还行。你有什么事？",
        "difficulty": "中等",
    },
    "犹豫观望型": {
        "company": "杭州智联商贸",
        "industry": "服务贸易",
        "current_channel": "无固定渠道",
        "volume": "30",
        "pain_points": "刚开始做东南亚，不太懂收款流程",
        "personality": "做事谨慎，不会轻易做决定。问很多问题，但很少当场答复。容易被吓到。",
        "opening": "你好，我是杭州智联的李经理。朋友推荐你们的，说做东南亚收款的？我们刚开始接触这块，很多东西不太懂。",
        "difficulty": "简单",
    },
    "技术导向型": {
        "company": "成都极光软件",
        "industry": "B2C电商（SaaS出海）",
        "current_channel": "空中云汇",
        "volume": "500",
        "pain_points": "API对接体验差、汇率不够优",
        "personality": "技术背景出身，关注API质量和技术细节。对商务话术不感冒，要看技术实力和数据。",
        "opening": "你好。我看了你们的官网，API文档在哪？我们现在用Airwallex，主要是API不够稳定，webhook经常延迟。你们的SLA是多少？",
        "difficulty": "困难",
    },
    "合规谨慎型": {
        "company": "上海严律合规咨询",
        "industry": "服务贸易（法律咨询）",
        "current_channel": "传统银行电汇",
        "volume": "120",
        "pain_points": "合规审查严格、对第三方支付平台信任度低",
        "personality": "极其重视合规和风险控制。每一个细节都要问清楚，喜欢看白纸黑字的证明文件。不接受模糊表述。",
        "opening": "你好，我是严律的合规总监张律师。你们Ksher是什么资质？先把你们的牌照复印件和审计报告发给我看看。",
        "difficulty": "困难",
    },
    "多方决策型": {
        "company": "北京联盛国际贸易集团",
        "industry": "B2B货贸（集团化）",
        "current_channel": "多家银行+万里汇",
        "volume": "2000",
        "pain_points": "决策链长、多部门意见不统一、切换成本高",
        "personality": "礼貌但非常谨慎。需要汇报CFO和CEO。关心ROI和迁移风险。喜欢看成功案例和数据。",
        "opening": "你好，我是联盛国际的采购部经理周磊。我们有多个部门在用不同的收款渠道，最近想整合一下。不过这事我说了不算，得过CFO和合规部那关。",
        "difficulty": "困难",
    },
}

# ---- 实战模拟：Mock对话树 ----
MOCK_DIALOG_TREES = {
    "价格敏感型": [
        {"trigger_keywords": ["费率", "价格", "多少钱", "成本"],
         "response": "嗯...0.05%起？那综合下来呢？加上汇兑佣金什么的，总共多少？别给我绕，直接说个数。"},
        {"trigger_keywords": ["银行", "对比", "节省", "隐性"],
         "response": "银行手续费确实不便宜...但我们用了好几年了，关系也熟。你说的隐性成本，具体能帮我省多少？"},
        {"trigger_keywords": ["试用", "免费", "体验", "0元"],
         "response": "0元开户倒是可以试试...不过你保证到账速度真的比银行快？我先试一笔小的。"},
        {"trigger_keywords": [],
         "response": "还有别的要跟我说的吗？你直接说重点。"},
    ],
    "品牌忠诚型": [
        {"trigger_keywords": ["东南亚", "牌照", "本地", "直连"],
         "response": "东南亚本地牌照？PingPong好像也能收东南亚的钱啊，有什么不一样？"},
        {"trigger_keywords": ["汇率", "锁汇", "省"],
         "response": "锁汇功能倒是有意思...PingPong好像没有。不过切换渠道挺麻烦的，对接、测试又要花时间。"},
        {"trigger_keywords": ["并行", "不影响", "逐步"],
         "response": "可以并行运行的话倒还好...我可以考虑先开个账户，但大部分量还是走PingPong。"},
        {"trigger_keywords": [],
         "response": "嗯，我理解了。不过我需要再想想，毕竟PingPong用了这么久了。"},
    ],
    "犹豫观望型": [
        {"trigger_keywords": ["安全", "牌照", "合规", "资金"],
         "response": "嗯嗯，牌照这些听起来挺正规的。但是我不太懂KYC这些，开户需要准备很多材料吗？"},
        {"trigger_keywords": ["简单", "流程", "材料", "开户"],
         "response": "营业执照和法人身份证就行？那倒不复杂。不过你们到账要多久？我们客户催得紧的话怕耽误事。"},
        {"trigger_keywords": ["T+1", "快", "工作日"],
         "response": "T+1挺快的...我回去跟老板说一下吧。能给我一份方案材料吗？我好给老板看。"},
        {"trigger_keywords": [],
         "response": "嗯...这个我需要再了解一下。你能把资料发我邮箱吗？"},
    ],
    "技术导向型": [
        {"trigger_keywords": ["API", "文档", "SDK", "对接"],
         "response": "RESTful API可以，webhook回调的延迟P99是多少？Airwallex那边经常5秒以上，很影响用户体验。"},
        {"trigger_keywords": ["毫秒", "延迟", "稳定", "SLA"],
         "response": "如果能保证在500ms以内还行。你们有沙箱环境吗？我想先跑一下压测。"},
        {"trigger_keywords": ["沙箱", "测试", "环境"],
         "response": "好，那先给我沙箱权限。另外问一下，你们支持多币种结算的API调用方式是怎样的？一个接口还是分币种？"},
        {"trigger_keywords": [],
         "response": "行，技术上我先看看文档和沙箱。费用那边你跟我们商务再对一下。"},
    ],
    "合规谨慎型": [
        {"trigger_keywords": ["牌照", "MSO", "BOT", "监管"],
         "response": "香港MSO和泰国BOT？这两个我知道。但你们在马来西亚和印尼的牌照是什么级别的？有没有当地央行的正式批文？"},
        {"trigger_keywords": ["审计", "报告", "认证", "PCI"],
         "response": "PCI DSS认证有了，那SOC2呢？我们内部合规要求必须有SOC2或等效审计报告。另外你们的反洗钱系统是自建还是第三方？"},
        {"trigger_keywords": ["托管", "隔离", "银行", "资金"],
         "response": "花旗和汇丰托管确实不错。那客户备付金的隔离机制是怎样的？有没有独立的第三方审计？"},
        {"trigger_keywords": [],
         "response": "嗯，你说的我先记下来。回头我要看书面材料，口头说的不算数。把相关文件准备好发我邮箱。"},
    ],
    "多方决策型": [
        {"trigger_keywords": ["案例", "客户", "同行", "谁在用"],
         "response": "有同行业的成功案例吗？最好是集团型企业的。我们CFO要看数据，不看故事。"},
        {"trigger_keywords": ["ROI", "节省", "成本", "省"],
         "response": "年省几十万这个数字不错，但我们体量大，切换成本也高。你能帮我做一份详细的ROI分析报告吗？我拿去给CFO看。"},
        {"trigger_keywords": ["迁移", "过渡", "并行", "切换"],
         "response": "并行期间两套系统的对账怎么处理？我们财务部最怕的就是账对不上。有没有专门的迁移方案？"},
        {"trigger_keywords": [],
         "response": "我个人觉得可以考虑，但最终还是要过CFO和合规部。你能准备一份正式的商务提案吗？我帮你推。"},
    ],
}

# ---- 考核中心：产品知识笔试题 ----
EXAM_QUESTIONS = {
    "选择题": [
        {"q": "Ksher 持有多少个国家/地区的本地支付牌照？",
         "options": ["A. 5个", "B. 8个", "C. 12个", "D. 3个"], "answer": "B"},
        {"q": "Ksher B2B 跨境收款的标准到账时效是？",
         "options": ["A. T+0", "B. T+1工作日", "C. T+3工作日", "D. T+5工作日"], "answer": "B"},
        {"q": "以下哪个不是 Ksher 的增值产品？",
         "options": ["A. 秒到宝", "B. 供应商付款", "C. 锁汇服务", "D. 贷款融资"], "answer": "D"},
        {"q": "Ksher 的 B2B 费率最低可以做到？",
         "options": ["A. 0.01%", "B. 0.05%", "C. 0.1%", "D. 0.5%"], "answer": "B"},
        {"q": "\"增量战场\"是指从哪类渠道抢客户？",
         "options": ["A. 竞品支付平台", "B. 银行", "C. 新客户", "D. 政府机构"], "answer": "B"},
        {"q": "Ksher 客户资金由哪类机构托管？",
         "options": ["A. Ksher自有账户", "B. 国际银行独立托管", "C. 第三方基金", "D. 区块链钱包"], "answer": "B"},
        {"q": "以下哪个属于\"存量战场\"的竞品？",
         "options": ["A. 招商银行", "B. PingPong", "C. 新客户", "D. 海关"], "answer": "B"},
        {"q": "Ksher 开户费是多少？",
         "options": ["A. 100元", "B. 500元", "C. 0元", "D. 1000元"], "answer": "C"},
        {"q": "服务贸易收款和货物贸易收款的主要区别是？",
         "options": ["A. 费率不同", "B. 所需单证不同", "C. 币种不同", "D. 没有区别"], "answer": "B"},
        {"q": "Ksher 的锁汇功能支持的最长远期是？",
         "options": ["A. 7天", "B. 30天", "C. 90天", "D. 365天"], "answer": "C"},
    ],
    "判断题": [
        {"q": "Ksher 只做东南亚市场，不支持欧美收款。", "answer": True,
         "explanation": "Ksher 专注东南亚8国跨境收款"},
        {"q": "使用 Ksher 收款需要缴纳月管理费。", "answer": False,
         "explanation": "Ksher 0月费，按实际交易量计费"},
        {"q": "KYC 是 Know Your Customer 的缩写，属于反洗钱合规要求。", "answer": True,
         "explanation": "KYC 是合规基本要求"},
        {"q": "所有客户的费率都是一样的，没有阶梯定价。", "answer": False,
         "explanation": "Ksher 根据月流水量进行阶梯定价"},
        {"q": "客户可以先免费试用，再决定是否正式使用。", "answer": True,
         "explanation": "0元开户，可小额试用"},
    ],
}

# ---- 竞品精简版（名称+攻击角度）----
COMPETITOR_QUICK_REF = {
    "PingPong": "欧美强但东南亚弱，无本地牌照，汇率加点高",
    "万里汇": "蚂蚁系但东南亚到账慢，费率含隐性成本",
    "XTransfer": "B2B见长但服务贸易弱，无锁汇功能",
    "连连支付": "老牌但技术老化，东南亚覆盖有限",
    "空中云汇": "API强但费率高，东南亚无本地牌照优势",
    "Payoneer": "全球覆盖但费率最高，中文服务差",
    "光子易": "新锐但规模小，牌照布局不如Ksher",
    "珊瑚跨境": "东南亚有布局但产品线单一",
}

# ---- AI出题：多角色异议池（Mock降级用）----
EXTRA_OBJECTION_POOL = {
    "采购负责人": [
        {"objection": "我们预算已经锁定给现有供应商了，今年不考虑新增",
         "context": "年度预算已分配", "difficulty": "中级",
         "key_elements": ["下一预算周期", "并行试用不占预算", "ROI数据"]},
        {"objection": "你们的合同条款太复杂了，能不能简化？",
         "context": "合同审批流程长", "difficulty": "中级",
         "key_elements": ["标准合同", "灵活条款", "法务对接"]},
        {"objection": "上次对接的另一家支付公司，服务承诺都没兑现",
         "context": "被竞品伤过", "difficulty": "高级",
         "key_elements": ["SLA保障", "专属客服", "违约赔偿机制"]},
    ],
    "技术负责人": [
        {"objection": "你们的API文档更新频率是多少？上次接了个平台文档和实际不一致",
         "context": "技术信任缺失", "difficulty": "中级",
         "key_elements": ["文档同步机制", "Changelog", "沙箱环境"]},
        {"objection": "我需要看你们的SOC2审计报告，合规部门要求的",
         "context": "内部合规要求", "difficulty": "高级",
         "key_elements": ["PCI DSS", "安全认证", "合规文件"]},
        {"objection": "webhook回调超时怎么处理？我们业务不能丢单",
         "context": "系统可靠性", "difficulty": "中级",
         "key_elements": ["重试机制", "消息队列", "SLA承诺"]},
    ],
    "财务负责人": [
        {"objection": "汇率波动风险怎么控制？上个季度因为汇率损失了8万",
         "context": "汇率风险敏感", "difficulty": "高级",
         "key_elements": ["锁汇功能", "远期合约", "风险对冲"]},
        {"objection": "你们的入账凭证格式和我们财务系统不兼容",
         "context": "系统对接问题", "difficulty": "中级",
         "key_elements": ["凭证格式", "API对账", "自定义导出"]},
        {"objection": "跨境收款的税务申报怎么处理？有完税证明吗？",
         "context": "税务合规", "difficulty": "高级",
         "key_elements": ["完税凭证", "税务申报支持", "合规流程"]},
    ],
}


# ============================================================
# 内容管理中心：存储工具
# ============================================================

def _get_materials_dir(kind: str) -> str:
    """返回 videos 或 docs 存储目录"""
    path = os.path.join(DATA_DIR, "training_materials", kind)
    os.makedirs(path, exist_ok=True)
    return path


def _materials_meta_path() -> str:
    base = os.path.join(DATA_DIR, "training_materials")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "metadata.json")


def _load_materials_meta() -> dict:
    path = _materials_meta_path()
    if not os.path.exists(path):
        return {"materials": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "materials" not in data:
                return {"materials": []}
            return data
    except Exception:
        return {"materials": []}


def _save_materials_meta(meta: dict):
    with open(_materials_meta_path(), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ============================================================
# 主渲染入口
# ============================================================

def render_role_trainer():
    """渲染话术培训师角色页面"""
    st.title("🎙️ 话术培训师 · AI陪练中心")
    st.markdown(
        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['md']};'>"
        "新人带教、话术练兵、异议攻防、实战模拟、通关考核——从菜鸟到高手的全链路训练"
        "</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    tab_onboard, tab_speech, tab_objection, tab_sim, tab_exam = st.tabs(
        ["新人带教", "话术练兵", "异议攻防", "实战模拟", "考核中心"]
    )

    with tab_onboard:
        _render_onboarding()

    with tab_speech:
        _render_speech_training()

    with tab_objection:
        _render_objection_training()

    with tab_sim:
        _render_simulation()

    with tab_exam:
        _render_exam_center()


# ============================================================
# Tab 1: 新人带教
# ============================================================

def _render_onboarding():
    """新人带教：30天入职计划"""
    st.markdown("**30天新人入职培训计划**")
    st.caption("结构化学习路径，从0到独立上岗。选择当前周次查看学习任务。")

    # 初始化进度
    if "onboard_progress" not in st.session_state:
        st.session_state.onboard_progress = {}

    week = st.selectbox(
        "当前学习阶段",
        options=list(ONBOARDING_PLAN.keys()),
        format_func=lambda k: ONBOARDING_PLAN[k]["title"],
        key="onboard_week_select",
    )

    plan = ONBOARDING_PLAN[week]

    # 主题卡片
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['primary'])},0.06);"
        f"border-left:3px solid {BRAND_COLORS['primary']};"
        f"padding:{SPACING['md']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;margin:{SPACING['sm']} 0;'>"
        f"<b>{plan['title']}</b><br>"
        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
        f"{plan['theme']}</span></div>",
        unsafe_allow_html=True,
    )

    # 学习目标
    st.markdown("**本周学习目标**")
    for obj in plan["objectives"]:
        st.markdown(f"- {obj}")

    # 课程列表（带完成勾选）
    st.markdown("---")
    st.markdown("**课程列表**")
    progress_key = f"onboard_{week}"
    if progress_key not in st.session_state.onboard_progress:
        st.session_state.onboard_progress[progress_key] = {}

    completed_count = 0
    total_count = len(plan["courses"])

    for i, course in enumerate(plan["courses"]):
        ck = f"{progress_key}_c{i}"
        done = st.checkbox(
            f"{'[必修]' if course['type'] == '必修' else '[选修]'} {course['name']} ({course['duration']})",
            value=st.session_state.onboard_progress[progress_key].get(ck, False),
            key=ck,
        )
        st.session_state.onboard_progress[progress_key][ck] = done
        if done:
            completed_count += 1

    # 进度条
    progress = completed_count / total_count if total_count > 0 else 0
    st.progress(progress, text=f"完成进度: {completed_count}/{total_count}")

    # 推荐练习 & 考核任务
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**推荐练习**")
        st.info(plan["practice"])
    with col2:
        st.markdown("**本周考核**")
        st.warning(plan["exam"])

    # 培训材料（视频+文档配对）
    _render_onboard_materials(week)

    # AI智能学习建议（V4增强）
    _render_ai_learning_advice()


def _render_onboard_materials(week: str):
    """在新人带教页展示当前周的培训材料（视频+文档配对）"""
    st.markdown("---")
    col_v, col_d = st.columns(2)

    meta = _load_materials_meta()
    items = [m for m in meta.get("materials", []) if m.get("week") == week or m.get("week") == "all"]

    # ── 视频区 ──
    with col_v:
        st.markdown("**📹 培训视频**")
        video_items = [m for m in items if m.get("video_filename")]
        if not video_items:
            st.markdown(
                f"<div style='border:1px dashed {BRAND_COLORS['border']};border-radius:0.5rem;"
                f"padding:1.5rem;text-align:center;color:{BRAND_COLORS['text_secondary']};font-size:0.85rem;'>"
                f"暂无视频<br><span style='font-size:0.75rem;'>管理员可在「内容管理中心」上传</span></div>",
                unsafe_allow_html=True,
            )
        else:
            for item in video_items:
                vid_path = os.path.join(_get_materials_dir("videos"), item["video_filename"])
                if not os.path.exists(vid_path):
                    continue
                with st.expander(f"▶ {item['title']}", expanded=False):
                    if item.get("description"):
                        st.caption(item["description"])
                    try:
                        st.video(vid_path)
                    except Exception:
                        with open(vid_path, "rb") as f:
                            st.download_button("下载视频", f, file_name=item["video_filename"],
                                               key=f"dl_v_{item['id']}")

    # ── 文档区 ──
    with col_d:
        st.markdown("**📄 学习文档**")
        doc_items = [m for m in items if m.get("doc_filename")]
        if not doc_items:
            st.markdown(
                f"<div style='border:1px dashed {BRAND_COLORS['border']};border-radius:0.5rem;"
                f"padding:1.5rem;text-align:center;color:{BRAND_COLORS['text_secondary']};font-size:0.85rem;'>"
                f"暂无文档<br><span style='font-size:0.75rem;'>管理员可在「内容管理中心」上传</span></div>",
                unsafe_allow_html=True,
            )
        else:
            for item in doc_items:
                doc_path = os.path.join(_get_materials_dir("docs"), item["doc_filename"])
                if not os.path.exists(doc_path):
                    continue
                ext = item["doc_filename"].rsplit(".", 1)[-1].upper()
                col1, col2 = st.columns([3, 1])
                with col1:
                    desc = f" — {item['description']}" if item.get("description") else ""
                    st.markdown(f"📄 **{item['title']}**{desc}")
                with col2:
                    with open(doc_path, "rb") as f:
                        st.download_button(f"下载 {ext}", f, file_name=item["doc_filename"],
                                           key=f"dl_d_{item['id']}")


def _render_ai_learning_advice():
    """AI分析考核成绩→推荐学习路径"""
    # 检查是否有考核数据
    exam_data = st.session_state.get("exam_scores", {})
    if not exam_data:
        return  # 无考核数据时不显示

    st.markdown("---")
    st.markdown("**AI 学习建议**")
    st.caption("基于你的考核成绩，AI分析薄弱环节并推荐个性化学习路径")

    if st.button("获取AI学习建议", key="ai_advice_btn"):
        with st.spinner("AI 正在分析你的学习情况..."):
            advice = _generate_learning_advice(exam_data)
            st.session_state.ai_learning_advice = advice

    advice = st.session_state.get("ai_learning_advice")
    if not advice:
        return

    # 展示建议
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['info'])},0.06);"
        f"border:1px solid {BRAND_COLORS['info']}30;border-radius:{RADIUS['md']};padding:{SPACING['md']};'>"
        f"<b>整体评估</b>：{advice.get('overall_assessment', '')}<br>"
        f"<b>薄弱环节</b>：{advice.get('weakest_area', '')}<br>"
        f"<b>推荐学习阶段</b>：{advice.get('recommended_week', '')}<br>"
        f"<b>预计达标天数</b>：{advice.get('estimated_days_to_ready', 'N/A')}天</div>",
        unsafe_allow_html=True,
    )

    actions = advice.get("priority_actions", [])
    if actions:
        st.markdown("**优先行动**")
        for i, a in enumerate(actions, 1):
            st.markdown(f"{i}. {a}")

    encouragement = advice.get("encouragement", "")
    if encouragement:
        st.success(encouragement)


def _generate_learning_advice(exam_data: dict) -> dict:
    """调用LLM生成学习建议，Mock降级"""
    # 从session读取各维度分数
    speech_scores = exam_data.get("speech_scores", {})
    objection_scores = exam_data.get("objection_scores", {})

    progress = st.session_state.get("onboard_progress", {})
    week_progress = {}
    for wk in ["week1", "week2", "week3", "week4"]:
        key = f"onboard_{wk}"
        items = progress.get(key, {})
        if items:
            done = sum(1 for v in items.values() if v)
            week_progress[wk] = int(done / len(items) * 100) if items else 0
        else:
            week_progress[wk] = 0

    user_msg = ADVISOR_USER_TEMPLATE.format(
        written_score=exam_data.get("written_total", 0),
        speech_score=speech_scores.get("total", 0),
        objection_score=objection_scores.get("total", 0),
        persuasion=speech_scores.get("persuasion", 5),
        expertise=speech_scores.get("expertise", 5),
        completeness=speech_scores.get("completeness", 5),
        compliance=speech_scores.get("compliance", 5),
        week1_progress=week_progress.get("week1", 0),
        week2_progress=week_progress.get("week2", 0),
        week3_progress=week_progress.get("week3", 0),
        week4_progress=week_progress.get("week4", 0),
    )

    llm_result = _llm_score(ADVISOR_SYSTEM_PROMPT, user_msg, agent_name="trainer_advisor")
    parsed = _parse_json_score(llm_result)
    if parsed and "weakest_area" in parsed:
        return parsed

    # Mock 降级
    return _mock_learning_advice(exam_data)


def _mock_learning_advice(exam_data: dict) -> dict:
    """Mock学习建议：取最低维度→推荐对应week"""
    speech = exam_data.get("speech_scores", {})
    written = exam_data.get("written_total", 60)

    dims = {
        "written": written / 10,
        "speech": speech.get("total", 20) / 4,
        "objection": exam_data.get("objection_scores", {}).get("total", 20) / 4,
    }
    weakest = min(dims, key=dims.get)

    week_map = {"written": "week1", "speech": "week2", "objection": "week3"}
    area_map = {"written": "产品知识", "speech": "话术表达", "objection": "异议处理"}

    return {
        "overall_assessment": f"{'产品知识基础扎实' if written >= 80 else '产品知识需要加强'}，{'话术表达有待提升' if dims['speech'] < 7 else '话术表达良好'}。",
        "weakest_area": area_map[weakest],
        "recommended_week": week_map[weakest],
        "priority_actions": [
            f"重点复习{area_map[weakest]}相关内容",
            "每天至少完成1次话术练习",
            "参加异议攻防训练提升应变能力",
        ],
        "estimated_days_to_ready": 7 if dims[weakest] >= 5 else 14,
        "encouragement": "每一次练习都在积累经验，坚持就能突破！",
    }


# ============================================================
# Tab 2: 话术练兵
# ============================================================

def _render_speech_training():
    """话术练兵：3种模式"""
    st.markdown("**话术练兵场**")
    st.caption("选择训练模式：看示范学标准 → 填空练实战 → 限时挑战测反应")

    mode = st.radio(
        "训练模式",
        options=["场景示范", "填空练习", "限时挑战"],
        horizontal=True,
        key="speech_train_mode",
    )

    if mode == "场景示范":
        _render_speech_demo()
    elif mode == "填空练习":
        _render_speech_practice()
    elif mode == "限时挑战":
        _render_speech_challenge()

    # 竞品速查（精简版）
    st.markdown("---")
    with st.expander("竞品速查参考（练习用）"):
        for name, angle in COMPETITOR_QUICK_REF.items():
            st.markdown(f"- **{name}**：{angle}")


def _render_speech_demo():
    """模式A：场景示范"""
    scene_name = st.selectbox(
        "选择话术场景",
        options=list(SPEECH_SCENES.keys()),
        key="speech_demo_scene",
    )
    scene = SPEECH_SCENES.get(scene_name, {})

    st.markdown(f"**场景说明**：{scene['description']}")
    st.markdown("---")

    # 标准话术
    st.markdown("**标准话术**")
    st.success(scene["standard_script"])

    # 关键要素
    st.markdown("**必须覆盖的关键要素**")
    cols = st.columns(len(scene["key_points"]))
    for i, kp in enumerate(scene["key_points"]):
        with cols[i % len(cols)]:
            st.markdown(
                f"<span style='background:{BRAND_COLORS['primary']}15;color:{BRAND_COLORS['primary']};"
                f"padding:{SPACING['xs']} {SPACING['sm']};border-radius:{RADIUS['sm']};font-size:{TYPE_SCALE['base']};'>{kp}</span>",
                unsafe_allow_html=True,
            )

    st.caption(f"提示：{scene['tips']}")

    # 复制按钮
    from ui.components.error_handlers import render_copy_button
    render_copy_button(scene["standard_script"])


def _render_speech_practice():
    """模式B：填空练习"""
    scene_name = st.selectbox(
        "选择练习场景",
        options=list(SPEECH_SCENES.keys()),
        key="speech_practice_scene",
    )
    scene = SPEECH_SCENES.get(scene_name, {})

    # 展示场景描述
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['info'])},0.08);"
        f"border-left:3px solid {BRAND_COLORS['info']};"
        f"padding:{SPACING['md']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;margin:{SPACING['sm']} 0;'>"
        f"<b>场景</b>：{scene['practice_scenario']}</div>",
        unsafe_allow_html=True,
    )

    # 用户输入
    user_answer = st.text_area(
        "写出你的话术回应",
        placeholder="请根据上述场景，写出你会对客户说的话...",
        height=150,
        key=f"speech_practice_answer_{scene_name}",
    )

    if st.button("提交并评分", type="primary", key=f"speech_practice_submit_{scene_name}"):
        if not user_answer.strip():
            st.warning("请输入你的话术回应")
            return

        with st.spinner("AI 正在评分..."):
            score_result = _score_speech(user_answer, scene)
            st.session_state[f"speech_score_{scene_name}"] = score_result

    # 显示评分结果
    result = st.session_state.get(f"speech_score_{scene_name}")
    if result:
        _render_score_card(result, scene["standard_script"], scene["key_points"])


def _render_speech_challenge():
    """模式C：限时挑战"""
    if "challenge_active" not in st.session_state:
        st.session_state.challenge_active = False
    if "challenge_scene" not in st.session_state:
        st.session_state.challenge_scene = None
    if "challenge_start_time" not in st.session_state:
        st.session_state.challenge_start_time = None

    if not st.session_state.challenge_active:
        st.markdown("随机抽取场景，限时60秒写出回应。准备好了吗？")
        if st.button("开始挑战", type="primary", key="challenge_start"):
            scene_name = random.choice(list(SPEECH_SCENES.keys()))
            st.session_state.challenge_scene = scene_name
            st.session_state.challenge_active = True
            st.session_state.challenge_start_time = time.time()
            st.rerun()
    else:
        scene_name = st.session_state.challenge_scene
        scene = SPEECH_SCENES.get(scene_name, {})

        # 倒计时提示
        elapsed = time.time() - st.session_state.challenge_start_time
        remaining = max(0, 60 - elapsed)
        if remaining > 0:
            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['warning'])},0.1);"
                f"padding:{SPACING['sm']} {SPACING['md']};border-radius:{RADIUS['md']};text-align:center;font-size:{TYPE_SCALE['xl']};'>"
                f"剩余时间：<b>{int(remaining)}</b> 秒</div>",
                unsafe_allow_html=True,
            )
        else:
            st.error("时间到！")

        st.markdown(f"**场景：{scene_name}**")
        st.markdown(f"> {scene['practice_scenario']}")

        answer = st.text_area(
            "快速写出你的回应",
            height=120,
            key="challenge_answer",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("提交", type="primary", key="challenge_submit"):
                if answer.strip():
                    with st.spinner("AI 评分中..."):
                        score_result = _score_speech(answer, scene)
                        elapsed_final = time.time() - st.session_state.challenge_start_time
                        score_result["time_used"] = f"{elapsed_final:.0f}秒"
                        st.session_state.challenge_result = score_result
                        st.session_state.challenge_active = False
                        st.rerun()
        with col2:
            if st.button("放弃", key="challenge_quit"):
                st.session_state.challenge_active = False
                st.rerun()

    # 展示上一轮结果
    cr = st.session_state.get("challenge_result")
    if cr and not st.session_state.challenge_active:
        st.markdown("---")
        st.markdown(f"**限时挑战结果** (用时：{cr.get('time_used', 'N/A')})")
        scene = SPEECH_SCENES.get(st.session_state.challenge_scene, {})
        _render_score_card(cr, scene.get("standard_script", ""), scene.get("key_points", []))


def _score_speech(user_answer: str, scene: dict) -> dict:
    """对话术回答进行AI教练深度点评，LLM优先，Mock降级"""
    standard = scene["standard_script"]
    key_points = scene["key_points"]

    # 尝试 LLM 教练点评（COACH_SYSTEM_PROMPT 含心理学框架）
    user_msg = COACH_USER_TEMPLATE.format(
        scene_name=scene.get("name", ""),
        scene_description=scene.get("description", ""),
        standard_script=standard,
        key_points=", ".join(key_points),
        user_answer=user_answer,
    )
    llm_result = _llm_score(COACH_SYSTEM_PROMPT, user_msg, agent_name="trainer_coach")
    parsed = _parse_json_score(llm_result)
    if parsed and "persuasion" in parsed:
        # 持久化训练结果
        _save_training_result("speech_coach", parsed)
        return parsed

    # Mock 降级：关键词匹配评分 + 技巧检测
    result = _mock_score_speech(user_answer, key_points)
    _save_training_result("speech_coach", result)
    return result


def _mock_score_speech(user_answer: str, key_points: list) -> dict:
    """Mock评分：关键词匹配 + 销售技巧检测"""
    answer_lower = user_answer.lower()
    hit_count = 0
    for kp in key_points:
        if kp.lower() in answer_lower or kp in user_answer:
            hit_count += 1

    coverage = hit_count / len(key_points) if key_points else 0
    base_score = 4 + int(coverage * 6)  # 4-10分

    persuasion = min(10, base_score + random.randint(-1, 1))
    expertise = min(10, base_score + random.randint(-1, 1))
    completeness = min(10, int(4 + coverage * 6))
    compliance = min(10, 7 + random.randint(0, 3))
    total = persuasion + expertise + completeness + compliance

    # 销售技巧检测（Mock关键词匹配）
    technique_keywords = {
        "社会证明": ["客户", "商家", "家", "用户", "案例", "都在用"],
        "损失厌恶": ["损失", "浪费", "错过", "亏", "少赚", "隐性成本"],
        "锚定效应": ["银行", "传统", "对比", "相比", "省"],
        "互惠原则": ["免费", "试用", "体验", "先", "赠送"],
        "稀缺性": ["限时", "名额", "仅", "最后", "活动"],
        "权威": ["牌照", "认证", "央行", "BOT", "MSO", "合规"],
        "镜像法": ["您说的", "您提到", "理解您"],
        "标注法": ["听起来", "看起来", "感觉您"],
    }
    techniques_used = []
    for tech_name, keywords in technique_keywords.items():
        for kw in keywords:
            if kw in user_answer:
                techniques_used.append({
                    "name": tech_name,
                    "quote": f"...{kw}...",
                    "effectiveness": "中" if coverage < 0.6 else "高",
                })
                break

    techniques_suggested = []
    all_techniques = ["社会证明", "损失厌恶", "锚定效应", "互惠原则", "稀缺性", "权威"]
    used_names = {t["name"] for t in techniques_used}
    for t in all_techniques:
        if t not in used_names:
            techniques_suggested.append(t)
            if len(techniques_suggested) >= 2:
                break

    missing = [kp for kp in key_points if kp not in user_answer]
    improvements = []
    if missing:
        improvements.append(f"建议覆盖以下关键要素：{', '.join(missing[:3])}")
    if len(user_answer) < 50:
        improvements.append("回答过于简短，建议增加更多细节")
    if "下一步" not in user_answer and "试用" not in user_answer:
        improvements.append("建议加入下一步行动号召（如邀请试用）")

    psychology_tip = "尝试使用「损失厌恶」：强调客户不使用Ksher每月会多花多少钱，比强调能省多少更有冲击力。"

    return {
        "persuasion": persuasion,
        "expertise": expertise,
        "completeness": completeness,
        "compliance": compliance,
        "total": total,
        "comment": f"覆盖了{hit_count}/{len(key_points)}个关键要素。{'表现不错！' if coverage >= 0.6 else '还需加强关键要素覆盖。'}",
        "improvements": improvements,
        "techniques_used": techniques_used,
        "techniques_suggested": techniques_suggested,
        "psychology_tip": psychology_tip,
    }


def _render_score_card(result: dict, standard_script: str = "", key_points: list = None):
    """渲染评分卡片"""
    total = result.get("total", 0)
    max_total = 40

    # 评级
    if total >= 36:
        grade, grade_color = "A", BRAND_COLORS["success"]
    elif total >= 28:
        grade, grade_color = "B", BRAND_COLORS["info"]
    elif total >= 20:
        grade, grade_color = "C", BRAND_COLORS["warning"]
    else:
        grade, grade_color = "D", BRAND_COLORS["danger"]

    # 总分卡片
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(grade_color)},0.08);"
        f"border:1px solid {grade_color}30;border-radius:{RADIUS['md']};padding:{SPACING['md']};text-align:center;'>"
        f"<span style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{grade_color};'>{grade}</span>"
        f"<span style='font-size:{TYPE_SCALE['lg']};color:{BRAND_COLORS['text_secondary']};margin-left:{SPACING['sm']};'>"
        f"{total}/{max_total}分</span></div>",
        unsafe_allow_html=True,
    )

    # 4维度分数
    dims = [
        ("说服力", result.get("persuasion", 0)),
        ("专业度", result.get("expertise", 0)),
        ("完整度", result.get("completeness", 0)),
        ("合规性", result.get("compliance", 0)),
    ]
    cols = st.columns(4)
    for i, (name, score) in enumerate(dims):
        with cols[i]:
            st.metric(name, f"{score}/10")

    # 评语
    comment = result.get("comment", "")
    if comment:
        st.markdown(f"**AI点评**：{comment}")

    # 销售技巧分析（V4增强）
    techniques_used = result.get("techniques_used", [])
    techniques_suggested = result.get("techniques_suggested", [])
    psychology_tip = result.get("psychology_tip", "")

    if techniques_used or techniques_suggested or psychology_tip:
        st.markdown("---")
        st.markdown("**销售技巧分析**")

        if techniques_used:
            st.markdown("已使用的技巧：")
            for t in techniques_used:
                eff = t.get("effectiveness", "中")
                eff_color = {"高": BRAND_COLORS["success"], "中": BRAND_COLORS["warning"], "低": BRAND_COLORS["danger"]}.get(eff, BRAND_COLORS["text_secondary"])
                st.markdown(
                    f"- **{t['name']}** <span style='color:{eff_color};font-size:{TYPE_SCALE['base']};'>[效果: {eff}]</span>"
                    f" — {t.get('quote', '')}",
                    unsafe_allow_html=True,
                )

        if techniques_suggested:
            st.markdown(f"建议尝试：{'、'.join(techniques_suggested)}")

        if psychology_tip:
            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['info'])},0.08);"
                f"border-left:3px solid {BRAND_COLORS['info']};padding:{SPACING['md']};border-radius:{RADIUS['sm']};"
                f"margin:{SPACING['sm']} 0;font-size:{TYPE_SCALE['md']};'>"
                f"心理学技巧提示：{psychology_tip}</div>",
                unsafe_allow_html=True,
            )

    # 改进建议
    improvements = result.get("improvements", [])
    if improvements:
        st.markdown("**改进建议**")
        for imp in improvements:
            st.markdown(f"- {imp}")

    # 标准答案对照
    if standard_script:
        with st.expander("查看标准话术"):
            st.success(standard_script)
            if key_points:
                st.markdown("**关键要素**：" + " | ".join(key_points))


# ============================================================
# Tab 3: 异议攻防
# ============================================================

def _render_objection_training():
    """异议攻防：题库练习 + AI出题双模式"""
    from ui.pages.objection_sim import BATTLEFIELD_OBJECTIONS

    st.markdown("**异议攻防训练**")
    st.caption("先写出你的回应，提交后对照标准答案，AI给出评分和改进建议")

    # 模式切换：题库练习 vs AI出题
    train_mode = st.radio(
        "训练模式",
        options=["题库练习", "AI出题"],
        horizontal=True,
        key="objection_train_mode",
    )

    if train_mode == "AI出题":
        _render_ai_objection_gen()
        return

    # === 题库练习模式（原有逻辑）===
    col1, col2 = st.columns(2)
    with col1:
        difficulty = st.selectbox(
            "难度",
            options=["初级", "中级", "高级"],
            key="objection_difficulty",
        )
    with col2:
        bf_filter = st.selectbox(
            "战场类型",
            options=["全部", "increment", "stock", "education"],
            format_func=lambda x: "全部战场" if x == "全部" else BATTLEFIELD_TYPES.get(x, {}).get("label", x),
            key="objection_bf_filter",
        )

    # 获取对应难度的异议（内置 + 自定义题库合并）
    objections = list(EXTENDED_OBJECTIONS.get(difficulty, []))
    try:
        import json as _json
        from config import DATA_DIR as _DATA_DIR
        _qb_file = os.path.join(_DATA_DIR, "objection_bank", "questions.json")
        if os.path.exists(_qb_file):
            with open(_qb_file, "r", encoding="utf-8") as _f:
                custom_qs = _json.load(_f)
            for q in custom_qs:
                if q.get("difficulty") == difficulty:
                    objections.append({
                        "objection": q.get("objection", ""),
                        "context": q.get("context", ""),
                        "battlefield": q.get("battlefield", ""),
                        "key_elements": [],
                        "_custom_responses": {
                            "direct": q.get("direct_response", ""),
                            "empathy": q.get("empathy_response", ""),
                            "data": q.get("data_response", ""),
                        },
                    })
    except Exception:
        pass
    if bf_filter != "全部":
        objections = [o for o in objections if o.get("battlefield") == bf_filter]

    if not objections:
        st.info("该筛选条件下暂无异议题目")
        return

    # 随机或顺序选题
    if "objection_idx" not in st.session_state:
        st.session_state.objection_idx = 0

    col_prev, col_next, col_rand = st.columns(3)
    with col_prev:
        if st.button("上一题", key="obj_prev"):
            st.session_state.objection_idx = max(0, st.session_state.objection_idx - 1)
            st.session_state.pop("obj_train_result", None)
    with col_next:
        if st.button("下一题", key="obj_next"):
            st.session_state.objection_idx = min(len(objections) - 1, st.session_state.objection_idx + 1)
            st.session_state.pop("obj_train_result", None)
    with col_rand:
        if st.button("随机抽题", key="obj_rand"):
            st.session_state.objection_idx = random.randint(0, len(objections) - 1)
            st.session_state.pop("obj_train_result", None)

    idx = st.session_state.objection_idx % len(objections)
    obj = objections[idx]

    # 展示异议
    st.markdown("---")
    bf_label = BATTLEFIELD_TYPES.get(obj.get("battlefield", ""), {}).get("label", "")
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['danger'])},0.06);"
        f"border-left:3px solid {BRAND_COLORS['danger']};"
        f"padding:{SPACING['md']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;'>"
        f"<span style='font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};'>"
        f"[{difficulty}] {bf_label}</span><br>"
        f"<b style='font-size:{TYPE_SCALE['lg']};'>客户说：「{obj['objection']}」</b><br>"
        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
        f"背景：{obj['context']}</span></div>",
        unsafe_allow_html=True,
    )

    # 用户作答
    user_response = st.text_area(
        "写出你的回应",
        placeholder="面对这个异议，你会怎么说？",
        height=150,
        key=f"obj_train_answer_{difficulty}_{idx}",
    )

    if st.button("提交并查看标准答案", type="primary", key=f"obj_train_submit_{difficulty}_{idx}"):
        if not user_response.strip():
            st.warning("请输入你的回应")
            return

        with st.spinner("AI 正在评分..."):
            # 从BATTLEFIELD_OBJECTIONS获取标准答案
            standard = _get_standard_objection_answer(obj)
            score_result = _score_objection(user_response, obj, standard)
            score_result["standard_answers"] = standard
            st.session_state.obj_train_result = score_result

    # 显示结果
    result = st.session_state.get("obj_train_result")
    if result:
        st.markdown("---")

        # AI评分
        _render_score_card(result)

        # 标准答案展示
        std = result.get("standard_answers", {})
        if std:
            st.markdown("---")
            st.markdown("**三种标准回应策略对照**")
            t1, t2, t3 = st.tabs(["直接回应", "共情回应", "数据回应"])
            with t1:
                st.info(std.get("direct", "暂无"))
            with t2:
                st.info(std.get("empathy", "暂无"))
            with t3:
                st.info(std.get("data", "暂无"))


def _render_ai_objection_gen():
    """AI出题模式：选角色+难度 → AI生成全新异议"""
    col1, col2 = st.columns(2)
    with col1:
        persona = st.selectbox(
            "买方角色",
            options=["采购负责人", "技术负责人", "财务负责人"],
            key="ai_obj_persona",
        )
    with col2:
        difficulty = st.selectbox(
            "难度",
            options=["初级", "中级", "高级"],
            key="ai_obj_difficulty",
        )

    if st.button("AI生成异议", type="primary", key="ai_obj_gen"):
        with st.spinner("AI 正在生成异议..."):
            obj = _generate_ai_objection(persona, difficulty)
            st.session_state.ai_generated_objection = obj
            st.session_state.pop("ai_obj_response_result", None)

    obj = st.session_state.get("ai_generated_objection")
    if not obj:
        return

    # 展示AI生成的异议
    st.markdown("---")
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['danger'])},0.06);"
        f"border-left:3px solid {BRAND_COLORS['danger']};"
        f"padding:{SPACING['md']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;'>"
        f"<span style='font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};'>"
        f"[{obj.get('difficulty', difficulty)}] {obj.get('persona', persona)}</span><br>"
        f"<b style='font-size:{TYPE_SCALE['lg']};'>客户说：「{obj.get('objection', '')}」</b><br>"
        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
        f"背景：{obj.get('context', '')}</span></div>",
        unsafe_allow_html=True,
    )

    # 提示回应要素
    key_elements = obj.get("key_elements", [])
    if key_elements:
        with st.expander("回应要素提示"):
            for el in key_elements:
                st.markdown(f"- {el}")

    # 用户作答
    user_response = st.text_area(
        "写出你的回应",
        placeholder="面对这个异议，你会怎么说？",
        height=150,
        key="ai_obj_user_response",
    )

    if st.button("提交回应", type="primary", key="ai_obj_submit"):
        if not user_response.strip():
            st.warning("请输入你的回应")
            return
        with st.spinner("AI 正在评分..."):
            score = _score_objection(user_response, obj, {
                "direct": obj.get("suggested_approach", ""),
                "empathy": "",
                "data": "",
            })
            _save_training_result("objection_ai", score)
            st.session_state.ai_obj_response_result = score

    result = st.session_state.get("ai_obj_response_result")
    if result:
        st.markdown("---")
        _render_score_card(result)
        approach = obj.get("suggested_approach", "")
        if approach:
            st.info(f"建议回应方向：{approach}")


def _generate_ai_objection(persona: str, difficulty: str) -> dict:
    """调用LLM生成异议，Mock降级"""
    existing = [o.get("objection", "") for o in
                st.session_state.get("ai_obj_history", [])]
    existing_text = "\n".join(f"- {e}" for e in existing) if existing else "（暂无）"

    user_msg = OBJECTION_GEN_USER_TEMPLATE.format(
        persona=persona,
        difficulty=difficulty,
        existing_objections=existing_text,
    )
    llm_result = _llm_score(OBJECTION_GEN_SYSTEM_PROMPT, user_msg,
                            agent_name="trainer_objection_gen")
    parsed = _parse_json_score(llm_result)
    if parsed and "objection" in parsed:
        # 记录历史避免重复
        if "ai_obj_history" not in st.session_state:
            st.session_state.ai_obj_history = []
        st.session_state.ai_obj_history.append(parsed)
        return parsed

    # Mock 降级
    return _mock_generate_objection(persona, difficulty)


def _mock_generate_objection(persona: str, difficulty: str) -> dict:
    """Mock异议生成：从EXTRA_OBJECTION_POOL随机选取"""
    pool = EXTRA_OBJECTION_POOL.get(persona, [])
    if not pool:
        return {
            "objection": "你们公司成立才几年，怎么保证不会跑路？",
            "context": "客户对公司资质有顾虑",
            "persona": persona,
            "difficulty": difficulty,
            "key_elements": ["公司历史", "牌照资质", "资金安全"],
            "suggested_approach": "展示牌照和监管资质，强调资金安全机制",
        }
    used = [o.get("objection", "") for o in
            st.session_state.get("ai_obj_history", [])]
    available = [o for o in pool if o.get("objection", "") not in used]
    if not available:
        available = pool
    choice = random.choice(available)
    choice["difficulty"] = difficulty
    return choice


def _get_standard_objection_answer(obj: dict) -> dict:
    """从BATTLEFIELD_OBJECTIONS获取匹配的标准答案（优先自定义题库）"""
    # 自定义题目直接带有回应
    if obj.get("_custom_responses"):
        return obj["_custom_responses"]

    from ui.pages.objection_sim import BATTLEFIELD_OBJECTIONS

    bf = obj.get("battlefield", "")
    obj_text = obj.get("objection", "")

    # 尝试精确匹配
    for o in BATTLEFIELD_OBJECTIONS.get(bf, []):
        if obj_text in o.get("objection", ""):
            return {
                "direct": o.get("direct_response", ""),
                "empathy": o.get("empathy_response", ""),
                "data": o.get("data_response", ""),
            }

    # 未匹配到，返回通用模板
    return {
        "direct": "直接回应：正面回应客户关切，用事实和数据说话，提供具体解决方案。",
        "empathy": "共情回应：先表示理解客户的顾虑，再用类似客户案例引导思考。",
        "data": "数据回应：用具体数字和案例证明价值，让数据说话。",
    }


def _score_objection(user_response: str, obj: dict, standard: dict) -> dict:
    """对异议回应进行AI评分"""
    # 尝试 LLM 评分
    llm_result = _llm_score(
        OBJECTION_SCORING_PROMPT,
        f"客户异议：{obj['objection']}\n"
        f"背景：{obj['context']}\n\n"
        f"标准直接回应：{standard.get('direct', '')}\n"
        f"标准共情回应：{standard.get('empathy', '')}\n"
        f"标准数据回应：{standard.get('data', '')}\n\n"
        f"用户回应：{user_response}\n\n"
        f"请评分并返回JSON。",
    )
    parsed = _parse_json_score(llm_result)
    if parsed and "persuasion" in parsed:
        _save_training_result("objection_score", parsed)
        return parsed

    # Mock 降级
    key_elements = obj.get("key_elements", [])
    result = _mock_score_speech(user_response, key_elements)
    _save_training_result("objection_score", result)
    return result


# ============================================================
# Tab 4: 实战模拟
# ============================================================

def _render_simulation():
    """实战模拟：AI扮演客户的自由对话（V4增强：阶段追踪+情绪系统）"""
    st.markdown("**实战模拟对话**")
    st.caption("选择客户类型，AI扮演客户和你对话。对话结束后给出综合评分。")

    # 初始化状态
    if "sim_active" not in st.session_state:
        st.session_state.sim_active = False
    if "sim_messages" not in st.session_state:
        st.session_state.sim_messages = []
    if "sim_persona" not in st.session_state:
        st.session_state.sim_persona = None
    if "sim_stage" not in st.session_state:
        st.session_state.sim_stage = "开场寒暄"
    if "sim_emotion" not in st.session_state:
        st.session_state.sim_emotion = "中性"

    if not st.session_state.sim_active:
        _render_simulation_setup()
    else:
        _render_simulation_dialog()


def _render_simulation_setup():
    """模拟设置页"""
    persona_name = st.selectbox(
        "选择客户类型",
        options=list(CUSTOMER_PERSONAS.keys()),
        key="sim_persona_select",
    )
    persona = CUSTOMER_PERSONAS.get(persona_name, {})
    if not persona:
        st.error("客户角色数据加载失败")
        return

    # 客户画像卡
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['info'])},0.06);"
        f"border:1px solid {BRAND_COLORS['info']}30;border-radius:{RADIUS['md']};padding:{SPACING['md']};'>"
        f"<b>{persona['company']}</b> · {persona['industry']} · 月流水{persona['volume']}万<br>"
        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
        f"现有渠道：{persona['current_channel']} | 痛点：{persona['pain_points']}<br>"
        f"性格：{persona['personality']}<br>"
        f"难度：{persona['difficulty']}</span></div>",
        unsafe_allow_html=True,
    )

    if st.button("开始模拟对话", type="primary", key="sim_start"):
        st.session_state.sim_active = True
        st.session_state.sim_persona = persona_name
        st.session_state.sim_messages = [
            {"role": "assistant", "content": persona["opening"]}
        ]
        st.session_state.sim_stage = "开场寒暄"
        st.session_state.sim_emotion = "中性"
        st.rerun()

    # 展示上一次的评分
    prev_score = st.session_state.get("sim_final_score")
    if prev_score:
        st.markdown("---")
        st.markdown("**上一次模拟评分**")
        _render_sim_score_card(prev_score)


def _render_simulation_dialog():
    """模拟对话界面（V4增强：阶段指示器+情绪显示）"""
    persona_name = st.session_state.sim_persona
    persona = CUSTOMER_PERSONAS.get(persona_name, {})

    st.markdown(f"**正在与「{persona.get('company', '')}」对话中...**")
    st.caption(f"客户类型：{persona_name} | 已进行 {len(st.session_state.sim_messages)} 轮")

    # 对话阶段进度条（V4增强）
    stages = ["开场寒暄", "需求挖掘", "产品推荐", "异议处理", "促成签约"]
    current_stage = st.session_state.get("sim_stage", "开场寒暄")
    stage_idx = stages.index(current_stage) if current_stage in stages else 0

    stage_html = f"<div style='display:flex;gap:{SPACING['xs']};margin:{SPACING['sm']} 0;'>"
    for i, s in enumerate(stages):
        if i < stage_idx:
            bg = BRAND_COLORS["success"]
            txt_c = "#fff"
        elif i == stage_idx:
            bg = BRAND_COLORS["primary"]
            txt_c = "#fff"
        else:
            bg = f"{BRAND_COLORS['border']}"
            txt_c = BRAND_COLORS["text_secondary"]
        stage_html += (
            f"<div style='flex:1;text-align:center;padding:{SPACING['xs']} 2px;border-radius:{RADIUS['sm']};"
            f"background:{bg};color:{txt_c};font-size:{TYPE_SCALE['sm']};'>{s}</div>"
        )
    stage_html += "</div>"
    st.markdown(stage_html, unsafe_allow_html=True)

    # 客户情绪显示（V4增强）
    emotion = st.session_state.get("sim_emotion", "中性")
    emotion_map = {
        "中性": ("--", BRAND_COLORS["text_secondary"]),
        "感兴趣": ("+", BRAND_COLORS["success"]),
        "怀疑": ("?", BRAND_COLORS["warning"]),
        "满意": ("++", BRAND_COLORS["success"]),
        "不耐烦": ("!", BRAND_COLORS["danger"]),
        "信任": ("+++", BRAND_COLORS["info"]),
    }
    emo_icon, emo_color = emotion_map.get(emotion, ("--", BRAND_COLORS["text_secondary"]))
    st.markdown(
        f"<div style='font-size:{TYPE_SCALE['base']};color:{emo_color};margin-bottom:{SPACING['sm']};'>"
        f"客户情绪：<b>{emotion}</b> {emo_icon}</div>",
        unsafe_allow_html=True,
    )

    # 显示对话历史
    for msg in st.session_state.sim_messages:
        if msg["role"] == "assistant":
            st.markdown(
                f"<div style='background:{BRAND_COLORS['surface']};border-radius:{RADIUS['md']};"
                f"padding:{SPACING['sm']} {SPACING['md']};margin:{SPACING['xs']} 0;'>"
                f"<b>客户</b>：{msg['content']}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['primary'])},0.06);"
                f"border-radius:{RADIUS['md']};padding:{SPACING['sm']} {SPACING['md']};margin:{SPACING['xs']} 0;'>"
                f"<b>你</b>：{msg['content']}</div>",
                unsafe_allow_html=True,
            )

    # 用户输入
    user_input = st.text_input(
        "你的回复",
        placeholder="输入你要对客户说的话...",
        key=f"sim_input_{len(st.session_state.sim_messages)}",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("发送", type="primary", key="sim_send"):
            if user_input.strip():
                st.session_state.sim_messages.append({"role": "user", "content": user_input.strip()})

                with st.spinner("客户思考中..."):
                    reply = _get_customer_reply(persona_name, persona, st.session_state.sim_messages)
                    st.session_state.sim_messages.append({"role": "assistant", "content": reply})
                st.rerun()

    with col2:
        if st.button("结束对话并评分", key="sim_end"):
            with st.spinner("AI 正在评估整场对话..."):
                score = _score_simulation(persona_name, persona, st.session_state.sim_messages)
                _save_training_result("simulation", score)
                st.session_state.sim_final_score = score
                st.session_state.sim_active = False
                st.rerun()


def _get_customer_reply(persona_name: str, persona: dict, messages: list) -> str:
    """获取客户回复：LLM优先（增强Prompt+META解析），Mock降级"""
    # 使用增强Prompt（含阶段+情绪追踪）
    system_prompt = ENHANCED_SIMULATION_SYSTEM_PROMPT_TEMPLATE.format(
        customer_type=persona_name,
        company=persona["company"],
        industry=persona["industry"],
        current_channel=persona["current_channel"],
        volume=persona["volume"],
        pain_points=persona["pain_points"],
        personality=persona["personality"],
    )

    reply = _llm_chat(system_prompt, messages, agent_name="trainer_simulator")
    if reply and not reply.startswith("[ERROR]"):
        # 解析META元数据（阶段+情绪）
        clean_text, meta = _parse_sim_metadata(reply)
        if meta:
            st.session_state.sim_stage = meta.get("stage", st.session_state.get("sim_stage", "开场寒暄"))
            st.session_state.sim_emotion = meta.get("emotion", st.session_state.get("sim_emotion", "中性"))
        return clean_text

    # Mock 降级：对话树 + Mock阶段情绪
    mock_reply = _mock_customer_reply(persona_name, messages)
    mock_meta = _mock_stage_emotion(messages)
    st.session_state.sim_stage = mock_meta.get("stage", "开场寒暄")
    st.session_state.sim_emotion = mock_meta.get("emotion", "中性")
    return mock_reply


def _mock_customer_reply(persona_name: str, messages: list) -> str:
    """Mock对话树回复"""
    tree = MOCK_DIALOG_TREES.get(persona_name, [])
    if not tree:
        return "嗯，我考虑一下吧。"

    # 获取用户最后一条消息
    last_user_msg = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            last_user_msg = msg["content"]
            break

    # 按关键词匹配
    for node in tree:
        keywords = node.get("trigger_keywords", [])
        if not keywords:
            continue
        for kw in keywords:
            if kw in last_user_msg:
                return node["response"]

    # 兜底：返回最后一个节点（通常是空关键词的通用回复）
    for node in reversed(tree):
        if not node.get("trigger_keywords"):
            return node["response"]

    return "嗯...我再想想，你还有别的要说的吗？"


def _score_simulation(persona_name: str, persona: dict, messages: list) -> dict:
    """对整场模拟对话进行评分"""
    # 构建对话文本
    dialog_text = ""
    for msg in messages:
        role = "客户" if msg["role"] == "assistant" else "销售"
        dialog_text += f"{role}：{msg['content']}\n"

    # 尝试 LLM 评分
    llm_result = _llm_score(
        SIMULATION_SCORING_PROMPT,
        f"客户类型：{persona_name}\n"
        f"客户公司：{persona['company']}\n"
        f"行业：{persona['industry']}\n"
        f"现有渠道：{persona['current_channel']}\n"
        f"月流水：{persona['volume']}万\n\n"
        f"对话记录：\n{dialog_text}\n\n"
        f"请评分并返回JSON。",
    )
    parsed = _parse_json_score(llm_result)
    if parsed and "opening" in parsed:
        return parsed

    # Mock 评分
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    total_words = sum(len(m) for m in user_msgs)
    num_rounds = len(user_msgs)

    opening = min(10, 5 + (2 if num_rounds >= 1 and len(user_msgs[0]) > 20 else 0))
    needs = min(10, 4 + min(3, num_rounds))
    product = min(10, 5 + (2 if total_words > 200 else 0))
    objection = min(10, 5 + (2 if num_rounds >= 3 else 0))
    closing = min(10, 4 + (3 if any("试" in m or "开户" in m for m in user_msgs) else 0))
    total = opening + needs + product + objection + closing

    return {
        "opening": opening,
        "needs_discovery": needs,
        "product_match": product,
        "objection_handling": objection,
        "closing": closing,
        "total": total,
        "comment": f"共进行{num_rounds}轮对话。{'对话较充分' if num_rounds >= 4 else '对话轮次偏少，建议多挖掘客户需求'}。",
        "highlights": ["参与了完整的对话流程"],
        "improvements": [
            "建议每轮对话都包含一个明确的推进动作",
            "注意在对话中穿插提问，了解客户真实需求",
        ],
    }


def _render_sim_score_card(result: dict):
    """渲染模拟评分卡"""
    total = result.get("total", 0)
    max_total = 50

    if total >= 42:
        grade, grade_color = "A", BRAND_COLORS["success"]
    elif total >= 35:
        grade, grade_color = "B", BRAND_COLORS["info"]
    elif total >= 25:
        grade, grade_color = "C", BRAND_COLORS["warning"]
    else:
        grade, grade_color = "D", BRAND_COLORS["danger"]

    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(grade_color)},0.08);"
        f"border:1px solid {grade_color}30;border-radius:{RADIUS['md']};padding:{SPACING['md']};text-align:center;'>"
        f"<span style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{grade_color};'>{grade}</span>"
        f"<span style='font-size:{TYPE_SCALE['lg']};color:{BRAND_COLORS['text_secondary']};margin-left:{SPACING['sm']};'>"
        f"{total}/{max_total}分</span></div>",
        unsafe_allow_html=True,
    )

    dims = [
        ("开场", result.get("opening", 0)),
        ("需求挖掘", result.get("needs_discovery", 0)),
        ("产品推荐", result.get("product_match", 0)),
        ("异议处理", result.get("objection_handling", 0)),
        ("促成签约", result.get("closing", 0)),
    ]
    cols = st.columns(5)
    for i, (name, score) in enumerate(dims):
        with cols[i]:
            st.metric(name, f"{score}/10")

    comment = result.get("comment", "")
    if comment:
        st.markdown(f"**AI点评**：{comment}")

    highlights = result.get("highlights", [])
    if highlights:
        st.markdown("**做得好的地方**")
        for h in highlights:
            st.markdown(f"- {h}")

    improvements = result.get("improvements", [])
    if improvements:
        st.markdown("**需要改进的地方**")
        for imp in improvements:
            st.markdown(f"- {imp}")


# ============================================================
# Tab 5: 考核中心
# ============================================================

def _render_exam_center():
    """考核中心"""
    st.markdown("**考核中心**")
    st.caption("产品知识笔试、话术实操考核、异议处理考核、综合成绩单")

    exam_type = st.radio(
        "考核类型",
        options=["产品知识笔试", "话术实操考核", "异议处理考核", "综合成绩单"],
        horizontal=True,
        key="exam_type",
    )

    if exam_type == "产品知识笔试":
        _render_written_exam()
    elif exam_type == "话术实操考核":
        _render_speech_exam()
    elif exam_type == "异议处理考核":
        _render_objection_exam()
    elif exam_type == "综合成绩单":
        _render_transcript()


def _render_written_exam():
    """产品知识笔试"""
    st.markdown("**产品知识笔试**")
    st.caption("10道选择题 + 5道判断题，80分及格")

    if "exam_submitted" not in st.session_state:
        st.session_state.exam_submitted = False

    if not st.session_state.exam_submitted:
        # 选择题
        st.markdown("#### 一、选择题（每题5分，共50分）")
        choice_answers = {}
        for i, q in enumerate(EXAM_QUESTIONS["选择题"]):
            choice_answers[i] = st.radio(
                f"{i+1}. {q['q']}",
                options=q["options"],
                key=f"exam_choice_{i}",
                index=None,
            )

        # 判断题
        st.markdown("#### 二、判断题（每题5分，共25分）")
        tf_answers = {}
        for i, q in enumerate(EXAM_QUESTIONS["判断题"]):
            tf_answers[i] = st.radio(
                f"{i+1}. {q['q']}",
                options=["正确", "错误"],
                key=f"exam_tf_{i}",
                index=None,
            )

        # 简答题占位
        st.markdown("#### 三、简答题（共25分）")
        sa1 = st.text_area(
            "1. 请用3句话介绍Ksher的核心优势（15分）",
            key="exam_sa_1",
            height=100,
        )
        sa2 = st.text_area(
            "2. 客户说'银行手续费也不高，为什么换？'，你会怎么回答？（10分）",
            key="exam_sa_2",
            height=100,
        )

        if st.button("提交试卷", type="primary", key="exam_submit"):
            score = 0

            # 选择题评分
            choice_correct = 0
            for i, q in enumerate(EXAM_QUESTIONS["选择题"]):
                ans = choice_answers.get(i, "")
                if ans and ans.startswith(q["answer"]):
                    choice_correct += 1
                    score += 5

            # 判断题评分
            tf_correct = 0
            for i, q in enumerate(EXAM_QUESTIONS["判断题"]):
                ans = tf_answers.get(i, "")
                correct_ans = "正确" if q["answer"] else "错误"
                if ans == correct_ans:
                    tf_correct += 1
                    score += 5

            # 简答题评分（简单评分）
            sa_score = 0
            if sa1.strip():
                sa_score += min(15, 5 + len(sa1.strip()) // 20 * 2)
            if sa2.strip():
                sa_score += min(10, 3 + len(sa2.strip()) // 20 * 2)
            score += sa_score

            st.session_state.exam_score = {
                "choice_correct": choice_correct,
                "choice_total": len(EXAM_QUESTIONS["选择题"]),
                "tf_correct": tf_correct,
                "tf_total": len(EXAM_QUESTIONS["判断题"]),
                "sa_score": sa_score,
                "total": score,
                "passed": score >= 80,
            }
            st.session_state.exam_submitted = True
            st.rerun()
    else:
        # 显示成绩
        result = st.session_state.exam_score
        passed = result["passed"]
        total = result["total"]

        color = BRAND_COLORS["success"] if passed else BRAND_COLORS["danger"]
        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(color)},0.08);"
            f"border:1px solid {color}30;border-radius:{RADIUS['md']};padding:{SPACING['md']};text-align:center;'>"
            f"<span style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{color};'>"
            f"{total}分</span>"
            f"<span style='font-size:{TYPE_SCALE['lg']};color:{BRAND_COLORS['text_secondary']};margin-left:{SPACING['sm']};'>"
            f"{'通过' if passed else '未通过'}（及格线80分）</span></div>",
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("选择题", f"{result['choice_correct']}/{result['choice_total']}")
        with col2:
            st.metric("判断题", f"{result['tf_correct']}/{result['tf_total']}")
        with col3:
            st.metric("简答题", f"{result['sa_score']}/25")

        if st.button("重新考试", key="exam_retry"):
            st.session_state.exam_submitted = False
            st.rerun()


def _render_speech_exam():
    """话术实操考核"""
    st.markdown("**话术实操考核**")
    st.caption("随机抽取1个话术场景，写出完整话术，AI评分")

    if "speech_exam_scene" not in st.session_state:
        st.session_state.speech_exam_scene = None

    if st.session_state.speech_exam_scene is None:
        if st.button("抽题", type="primary", key="speech_exam_draw"):
            st.session_state.speech_exam_scene = random.choice(list(SPEECH_SCENES.keys()))
            st.rerun()
        return

    scene_name = st.session_state.speech_exam_scene
    scene = SPEECH_SCENES.get(scene_name, {})

    st.markdown(f"**考核场景：{scene_name}**")
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['info'])},0.08);"
        f"padding:{SPACING['md']} {SPACING['md']};border-radius:{RADIUS['md']};'>{scene['practice_scenario']}</div>",
        unsafe_allow_html=True,
    )

    answer = st.text_area(
        "写出你的完整话术",
        height=200,
        key="speech_exam_answer",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("提交考核", type="primary", key="speech_exam_submit"):
            if answer.strip():
                with st.spinner("AI 评分中..."):
                    result = _score_speech(answer, scene)
                    st.session_state.speech_exam_result = result
                    # 保存到综合成绩
                    st.session_state.setdefault("exam_results", {})["speech"] = result
    with col2:
        if st.button("重新抽题", key="speech_exam_redraw"):
            st.session_state.speech_exam_scene = None
            st.session_state.pop("speech_exam_result", None)
            st.rerun()

    result = st.session_state.get("speech_exam_result")
    if result:
        _render_score_card(result, scene["standard_script"], scene["key_points"])


def _render_objection_exam():
    """异议处理考核"""
    st.markdown("**异议处理考核**")
    st.caption("随机抽取3个异议，逐一回答，取平均分")

    if "obj_exam_questions" not in st.session_state:
        st.session_state.obj_exam_questions = None

    if st.session_state.obj_exam_questions is None:
        if st.button("抽题（3道异议）", type="primary", key="obj_exam_draw"):
            all_objs = []
            for level_objs in EXTENDED_OBJECTIONS.values():
                all_objs.extend(level_objs)
            st.session_state.obj_exam_questions = random.sample(all_objs, min(3, len(all_objs)))
            st.rerun()
        return

    questions = st.session_state.obj_exam_questions
    answers = {}

    for i, obj in enumerate(questions):
        st.markdown(f"---\n**异议 {i+1}**：{obj['objection']}")
        st.caption(f"背景：{obj['context']}")
        answers[i] = st.text_area(
            f"你的回应（第{i+1}题）",
            height=120,
            key=f"obj_exam_answer_{i}",
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("提交全部", type="primary", key="obj_exam_submit"):
            if all(a.strip() for a in answers.values()):
                with st.spinner("AI 逐题评分中..."):
                    scores = []
                    for i, obj in enumerate(questions):
                        standard = _get_standard_objection_answer(obj)
                        score = _score_objection(answers[i], obj, standard)
                        scores.append(score)

                    # 计算平均
                    avg = {
                        "persuasion": sum(s.get("persuasion", 0) for s in scores) // len(scores),
                        "expertise": sum(s.get("expertise", 0) for s in scores) // len(scores),
                        "completeness": sum(s.get("completeness", 0) for s in scores) // len(scores),
                        "compliance": sum(s.get("compliance", 0) for s in scores) // len(scores),
                    }
                    avg["total"] = sum(avg.values())
                    avg["comment"] = f"3道异议平均得分 {avg['total']}/40。"
                    avg["improvements"] = list({imp for s in scores for imp in s.get("improvements", [])})[:3]

                    st.session_state.obj_exam_result = avg
                    st.session_state.setdefault("exam_results", {})["objection"] = avg
            else:
                st.warning("请回答所有题目")
    with col2:
        if st.button("重新抽题", key="obj_exam_redraw"):
            st.session_state.obj_exam_questions = None
            st.session_state.pop("obj_exam_result", None)
            st.rerun()

    result = st.session_state.get("obj_exam_result")
    if result:
        st.markdown("---")
        st.markdown("**异议处理考核结果（3题平均）**")
        _render_score_card(result)


def _render_transcript():
    """综合成绩单（V4增强：雷达图+AI训练报告+历史记录）"""
    st.markdown("**综合成绩单**")
    st.caption("汇总笔试、话术实操、异议处理各项成绩")

    results = st.session_state.get("exam_results", {})
    written = st.session_state.get("exam_score")
    speech = results.get("speech")
    objection = results.get("objection")

    # 笔试
    st.markdown("---")
    st.markdown("**1. 产品知识笔试**")
    if written:
        st.metric("笔试分数", f"{written['total']}/100", delta="通过" if written["passed"] else "未通过")
    else:
        st.info("尚未完成笔试")

    # 话术实操
    st.markdown("**2. 话术实操考核**")
    if speech:
        st.metric("话术得分", f"{speech.get('total', 0)}/40")
    else:
        st.info("尚未完成话术考核")

    # 异议处理
    st.markdown("**3. 异议处理考核**")
    if objection:
        st.metric("异议处理得分", f"{objection.get('total', 0)}/40")
    else:
        st.info("尚未完成异议处理考核")

    # 综合评级
    st.markdown("---")
    st.markdown("**综合评级**")

    if written and speech and objection:
        # 归一化到100分制
        written_norm = written["total"]  # /100
        speech_norm = speech.get("total", 0) * 2.5  # /40 → /100
        objection_norm = objection.get("total", 0) * 2.5  # /40 → /100
        composite = (written_norm * 0.3 + speech_norm * 0.35 + objection_norm * 0.35)

        if composite >= 90:
            grade, grade_color = "A", BRAND_COLORS["success"]
        elif composite >= 75:
            grade, grade_color = "B", BRAND_COLORS["info"]
        elif composite >= 60:
            grade, grade_color = "C", BRAND_COLORS["warning"]
        else:
            grade, grade_color = "D", BRAND_COLORS["danger"]

        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(grade_color)},0.08);"
            f"border:1px solid {grade_color}30;border-radius:{RADIUS['md']};padding:{SPACING['lg']};text-align:center;'>"
            f"<span style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{grade_color};'>{grade}</span><br>"
            f"<span style='font-size:{TYPE_SCALE['xl']};'>综合得分：{composite:.0f}分</span><br>"
            f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
            f"笔试{written_norm:.0f} × 30% + 话术{speech_norm:.0f} × 35% + 异议{objection_norm:.0f} × 35%"
            f"</span></div>",
            unsafe_allow_html=True,
        )

        # 保存到exam_scores供AI学习建议使用
        st.session_state.exam_scores = {
            "written_total": written["total"],
            "speech_scores": speech,
            "objection_scores": objection,
        }

        # 技能雷达图（V4增强）
        _render_skill_radar(written, speech, objection)

        # AI训练报告（V4增强）
        _render_training_report(written, speech, objection)

        # 弱项分析
        st.markdown("**弱项分析**")
        scores_map = {"笔试": written_norm, "话术": speech_norm, "异议处理": objection_norm}
        weakest = min(scores_map, key=scores_map.get)
        st.markdown(f"- 最弱项：**{weakest}**（{scores_map[weakest]:.0f}分）")
        if weakest == "笔试":
            st.markdown("- 建议：回到「新人带教 → Week 1」复习产品知识")
        elif weakest == "话术":
            st.markdown("- 建议：多做「话术练兵 → 填空练习」训练")
        else:
            st.markdown("- 建议：多做「异议攻防」中级和高级训练")
    else:
        missing = []
        if not written:
            missing.append("产品知识笔试")
        if not speech:
            missing.append("话术实操考核")
        if not objection:
            missing.append("异议处理考核")
        st.info(f"请先完成以下考核：{', '.join(missing)}")

    # 历史训练记录（V4增强）
    _render_training_history()


def _render_skill_radar(written: dict, speech: dict, objection: dict):
    """渲染5维技能雷达图"""
    st.markdown("---")
    st.markdown("**技能雷达图**")

    # 5维度归一化到0-10
    product_knowledge = min(10, written["total"] / 10)
    persuasion = speech.get("persuasion", 5)
    expertise = speech.get("expertise", 5)
    objection_handling = min(10, objection.get("total", 20) / 4)
    compliance = speech.get("compliance", 5)

    categories = ["产品知识", "说服力", "专业度", "异议处理", "合规性"]
    values = [product_knowledge, persuasion, expertise, objection_handling, compliance]
    # 闭合雷达图
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        fillcolor=f"rgba({hex_to_rgb(BRAND_COLORS['primary'])},0.15)",
        line=dict(color=BRAND_COLORS["primary"], width=2),
        name="当前水平",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=10)),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        margin=dict(l=60, r=60, t=30, b=30),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_training_report(written: dict, speech: dict, objection: dict):
    """AI训练报告"""
    st.markdown("---")
    st.markdown("**AI 综合训练报告**")

    if st.button("生成AI训练报告", key="gen_training_report"):
        with st.spinner("AI 正在生成综合训练报告..."):
            report = _generate_training_report(written, speech, objection)
            _save_training_result("training_report", report)
            st.session_state.training_report = report

    report = st.session_state.get("training_report")
    if not report:
        return

    # 评级展示
    grade = report.get("overall_grade", "C")
    grade_colors = {"A": BRAND_COLORS["success"], "B": BRAND_COLORS["info"],
                    "C": BRAND_COLORS["warning"], "D": BRAND_COLORS["danger"]}
    gc = grade_colors.get(grade, BRAND_COLORS["text_secondary"])

    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(gc)},0.08);"
        f"border:1px solid {gc}30;border-radius:{RADIUS['md']};padding:{SPACING['md']};text-align:center;'>"
        f"<span style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{gc};'>评级 {grade}</span>"
        f"<span style='font-size:{TYPE_SCALE['lg']};color:{BRAND_COLORS['text_secondary']};margin-left:{SPACING['sm']};'>"
        f"综合分 {report.get('overall_score', 0)}</span><br>"
        f"<span style='font-size:{TYPE_SCALE['md']};'>{report.get('readiness', '')}</span></div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**优势**")
        for s in report.get("strengths", []):
            st.markdown(f"- {s}")
    with col2:
        st.markdown("**不足**")
        for w in report.get("weaknesses", []):
            st.markdown(f"- {w}")

    # 改进计划
    plan = report.get("improvement_plan", [])
    if plan:
        st.markdown("**改进计划**")
        for item in plan:
            priority = item.get("priority", "medium")
            p_color = {"high": BRAND_COLORS["danger"], "medium": BRAND_COLORS["warning"],
                       "low": BRAND_COLORS["success"]}.get(priority, BRAND_COLORS["text_secondary"])
            st.markdown(
                f"- <span style='color:{p_color};'>[{priority}]</span> "
                f"**{item.get('area', '')}**：{item.get('action', '')} "
                f"（预计{item.get('estimated_days', '?')}天）",
                unsafe_allow_html=True,
            )

    milestone = report.get("next_milestone", "")
    if milestone:
        st.info(f"下一里程碑：{milestone}")

    coaching = report.get("coaching_note", "")
    if coaching:
        st.caption(f"培训负责人提示：{coaching}")


def _generate_training_report(written: dict, speech: dict, objection: dict) -> dict:
    """调用LLM生成训练报告，Mock降级"""
    # 构建历史记录文本
    history = _load_training_history(limit=10)
    history_text = ""
    for h in history[:10]:
        history_text += f"- [{h.get('timestamp', '')}] {h.get('type', '')}: {json.dumps(h.get('data', {}), ensure_ascii=False)[:100]}\n"
    if not history_text:
        history_text = "（暂无历史记录）"

    speech_scores_text = f"说服力{speech.get('persuasion', 0)}/专业度{speech.get('expertise', 0)}/完整度{speech.get('completeness', 0)}/合规性{speech.get('compliance', 0)}, 总分{speech.get('total', 0)}/40"
    objection_scores_text = f"说服力{objection.get('persuasion', 0)}/专业度{objection.get('expertise', 0)}/完整度{objection.get('completeness', 0)}/合规性{objection.get('compliance', 0)}, 总分{objection.get('total', 0)}/40"

    user_msg = REPORTER_USER_TEMPLATE.format(
        written_total=written["total"],
        speech_scores=speech_scores_text,
        objection_scores=objection_scores_text,
        training_history=history_text,
    )

    llm_result = _llm_score(REPORTER_SYSTEM_PROMPT, user_msg, agent_name="trainer_reporter")
    parsed = _parse_json_score(llm_result)
    if parsed and "overall_grade" in parsed:
        return parsed

    return _mock_training_report(written, speech, objection)


def _mock_training_report(written: dict, speech: dict, objection: dict) -> dict:
    """Mock训练报告"""
    written_score = written["total"]
    speech_total = speech.get("total", 20)
    obj_total = objection.get("total", 20)

    composite = written_score * 0.3 + speech_total * 2.5 * 0.35 + obj_total * 2.5 * 0.35

    if composite >= 90:
        grade = "A"
    elif composite >= 75:
        grade = "B"
    elif composite >= 60:
        grade = "C"
    else:
        grade = "D"

    strengths = []
    weaknesses = []
    if written_score >= 80:
        strengths.append("产品知识基础扎实")
    else:
        weaknesses.append("产品知识掌握不足")
    if speech_total >= 30:
        strengths.append("话术表达能力较强")
    else:
        weaknesses.append("话术表达有待提升")
    if obj_total >= 30:
        strengths.append("异议处理反应良好")
    else:
        weaknesses.append("异议处理能力需加强")

    plan = []
    if "产品知识" in " ".join(weaknesses):
        plan.append({"area": "产品知识", "action": "重新学习Week1课程，重点费率和牌照", "priority": "high", "estimated_days": 5})
    if "话术" in " ".join(weaknesses):
        plan.append({"area": "话术表达", "action": "每天完成2次话术练习", "priority": "high", "estimated_days": 7})
    if "异议" in " ".join(weaknesses):
        plan.append({"area": "异议处理", "action": "完成异议攻防全部中级题目", "priority": "medium", "estimated_days": 5})

    readiness_map = {"A": "可以独立上岗", "B": "需要继续培训", "C": "需要继续培训", "D": "建议重新学习"}

    return {
        "overall_grade": grade,
        "overall_score": int(composite),
        "strengths": strengths or ["学习态度积极"],
        "weaknesses": weaknesses or ["各方面均需提升"],
        "improvement_plan": plan or [{"area": "综合能力", "action": "系统学习全部4周课程", "priority": "high", "estimated_days": 14}],
        "next_milestone": "完成所有考核并达到B级以上",
        "readiness": readiness_map.get(grade, "需要继续培训"),
        "coaching_note": "建议安排一次真实客户陪访，在实战中检验培训效果。",
    }


def _render_training_history():
    """展示历史训练记录"""
    history = _load_training_history(limit=20)
    if not history:
        return

    st.markdown("---")
    with st.expander(f"历史训练记录（近{len(history)}条）"):
        for h in history:
            ts = h.get("timestamp", "")[:16]
            rtype = h.get("type", "unknown")
            data = h.get("data", {})

            type_labels = {
                "speech_coach": "话术点评",
                "objection_ai": "异议训练",
                "simulation": "实战模拟",
                "training_report": "训练报告",
            }
            label = type_labels.get(rtype, rtype)

            score_text = ""
            if "total" in data:
                score_text = f" — {data['total']}分"
            elif "overall_grade" in data:
                score_text = f" — {data['overall_grade']}级"

            st.markdown(f"- `{ts}` **{label}**{score_text}")
