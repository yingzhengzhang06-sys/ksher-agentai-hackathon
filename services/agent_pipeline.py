"""
多Agent协作流水线 — 原生实现（替代CrewAI）

基于 LLMClient 实现顺序调用的多Agent工作流：
- 工作流A：内容生产流水线（Researcher → Writer → Editor → Adapter）
- 工作流B：竞品分析自动化（Crawler → Analyzer → Reporter）

每个Agent是一次独立的LLM调用，上一个Agent的输出作为下一个的输入。
"""

import json
from typing import Optional


# ============================================================
# 工作流A：内容生产流水线
# ============================================================

_RESEARCHER_SYSTEM = """你是一位资深市场调研员，专注跨境支付和东南亚市场。
你的任务是分析给定主题，输出结构化的调研报告，包含：
1. 主题概述（1-2句话定义主题）
2. 目标受众画像（年龄/职业/痛点）
3. 热点角度（3-5个可写的切入点）
4. 关键数据点（数字/比例/趋势）
5. 竞品在该主题上的动态
请用中文输出，条理清晰。"""

_WRITER_SYSTEM = """你是一位高级内容写手，擅长B2B金融科技领域的内容创作。
基于调研报告，撰写一篇完整的营销内容初稿。要求：
1. 标题吸引眼球（带数字或悬念）
2. 开头有钩子（痛点/问题/场景）
3. 正文有论据支撑（数据/案例/对比）
4. 结尾有CTA（行动号召）
5. 语言口语化但专业，适合社交媒体传播
字数800-1200字，中文。"""

_EDITOR_SYSTEM = """你是一位资深内容编辑，负责审稿和润色。
对初稿进行以下优化：
1. 检查事实准确性（标注存疑数据）
2. 优化标题（更吸引眼球）
3. 删除冗余表述，使语言精炼
4. 增强金句和记忆点
5. 确保品牌调性统一（Ksher风格：专业但亲切，数据驱动）
6. 检查是否有敏感内容
直接输出润色后的完整文章，不要输出修改说明。"""

_ADAPTER_SYSTEM = """你是一位全平台内容适配专家。
将一篇完整文章适配为不同平台的格式。请为每个指定平台输出一个版本：

**朋友圈版**：3-5行，带emoji，口语化，结尾互动
**公众号版**：保留完整结构，加粗重点，适合长文阅读
**小红书版**：标题带emoji+数字，正文分段短句，结尾加话题标签

请用分隔线区分每个平台版本。每个版本标注【朋友圈版】【公众号版】【小红书版】。"""


def run_content_pipeline(topic: str, platforms: list, llm_client,
                         callback=None) -> dict:
    """
    内容生产流水线：4个Agent顺序执行

    Args:
        topic: 内容主题
        platforms: 目标平台列表 ["moments", "wechat_mp", "xhs"]
        llm_client: LLMClient实例
        callback: 进度回调 callback(step, total, step_name, result)

    Returns:
        {
            "success": bool,
            "research": str,
            "draft": str,
            "edited": str,
            "adapted": str,
            "error": str,
        }
    """
    result = {
        "success": False,
        "research": "",
        "draft": "",
        "edited": "",
        "adapted": "",
        "error": "",
    }

    platform_names = {
        "moments": "朋友圈",
        "wechat_mp": "公众号",
        "xhs": "小红书",
    }
    platform_str = "、".join([platform_names.get(p, p) for p in platforms])

    try:
        # Step 1: 调研
        if callback:
            callback(1, 4, "调研分析", None)
        research = llm_client.call_sync(
            agent_name="pipeline_researcher",
            system=_RESEARCHER_SYSTEM,
            user_msg=f"请对以下主题进行深度调研：\n\n主题：{topic}\n\n目标平台：{platform_str}",
        )
        result["research"] = research

        # Step 2: 撰写
        if callback:
            callback(2, 4, "内容撰写", research)
        draft = llm_client.call_sync(
            agent_name="pipeline_writer",
            system=_WRITER_SYSTEM,
            user_msg=f"基于以下调研报告，撰写营销内容初稿：\n\n{research}\n\n主题：{topic}\n品牌：Ksher（东南亚跨境收款专家，8国本地牌照）",
        )
        result["draft"] = draft

        # Step 3: 润色
        if callback:
            callback(3, 4, "编辑润色", draft)
        edited = llm_client.call_sync(
            agent_name="pipeline_editor",
            system=_EDITOR_SYSTEM,
            user_msg=f"请对以下初稿进行审稿和润色：\n\n{draft}",
        )
        result["edited"] = edited

        # Step 4: 适配
        if callback:
            callback(4, 4, "平台适配", edited)
        adapted = llm_client.call_sync(
            agent_name="pipeline_adapter",
            system=_ADAPTER_SYSTEM,
            user_msg=f"请将以下文章适配为这些平台的格式：{platform_str}\n\n{edited}",
        )
        result["adapted"] = adapted
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


# ============================================================
# 工作流B：竞品分析自动化
# ============================================================

_ANALYZER_SYSTEM = """你是一位竞品分析专家，专注跨境支付行业。
基于收集到的竞品社交媒体内容，进行以下分析：
1. **内容策略**：竞品主要发什么类型的内容（教程/案例/新闻/促销）
2. **发布频率**：推断其内容发布节奏
3. **受众定位**：内容面向谁（行业/规模/需求）
4. **优势卖点**：竞品反复强调的核心卖点
5. **内容风格**：语言风格/视觉风格/互动方式
6. **薄弱环节**：竞品内容中的缺失或不足

用数据说话，给出具体例子。"""

_REPORTER_SYSTEM = """你是一位高级商业分析师，负责撰写竞品分析报告。
基于分析结果，生成一份结构化报告：

# 竞品内容分析报告

## 1. 执行摘要（3句话概括）
## 2. 竞品内容策略矩阵
## 3. 竞品 vs Ksher对比
## 4. 可借鉴的优秀做法
## 5. 我方差异化机会
## 6. 行动建议（具体可执行的3-5条）

报告要专业但简洁，适合管理层阅读。"""


def run_competitive_analysis(competitor_name: str, competitor_info: dict,
                             social_posts: list, llm_client,
                             callback=None) -> dict:
    """
    竞品分析工作流：3个Agent顺序执行

    Args:
        competitor_name: 竞品名称
        competitor_info: 竞品基础信息（来自competitor_knowledge.py）
        social_posts: 社交媒体帖子列表（SocialPost.to_dict()）
        llm_client: LLMClient实例
        callback: 进度回调

    Returns:
        {
            "success": bool,
            "posts_summary": str,
            "analysis": str,
            "report": str,
            "error": str,
        }
    """
    result = {
        "success": False,
        "posts_summary": "",
        "analysis": "",
        "report": "",
        "error": "",
    }

    try:
        # Step 1: 整理社交媒体内容
        if callback:
            callback(1, 3, "内容整理", None)

        posts_text = f"竞品：{competitor_name}\n"
        if competitor_info:
            posts_text += f"基础信息：{json.dumps(competitor_info, ensure_ascii=False)[:1000]}\n\n"
        posts_text += "社交媒体内容：\n"
        for i, post in enumerate(social_posts[:20], 1):
            p = post if isinstance(post, dict) else post.to_dict()
            posts_text += (
                f"\n--- 帖子{i} [{p.get('platform', '')}] ---\n"
                f"标题：{p.get('title', '')}\n"
                f"内容：{p.get('content', '')[:300]}\n"
                f"互动：{p.get('likes', 0)}赞 {p.get('comments', 0)}评论\n"
            )
        result["posts_summary"] = posts_text

        # Step 2: 深度分析
        if callback:
            callback(2, 3, "深度分析", posts_text)
        analysis = llm_client.call_sync(
            agent_name="pipeline_analyzer",
            system=_ANALYZER_SYSTEM,
            user_msg=f"请分析以下竞品的社交媒体内容策略：\n\n{posts_text}",
        )
        result["analysis"] = analysis

        # Step 3: 生成报告
        if callback:
            callback(3, 3, "报告生成", analysis)
        report = llm_client.call_sync(
            agent_name="pipeline_reporter",
            system=_REPORTER_SYSTEM,
            user_msg=(
                f"基于以下竞品分析结果，生成正式的竞品分析报告：\n\n"
                f"竞品：{competitor_name}\n\n"
                f"分析结果：\n{analysis}\n\n"
                f"我方品牌：Ksher（东南亚跨境收款专家，8国本地牌照，T+1到账，费率0.05%起）"
            ),
        )
        result["report"] = report
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


# ============================================================
# Mock 降级
# ============================================================

def mock_content_pipeline(topic: str, platforms: list) -> dict:
    """Mock内容生产流水线结果"""
    return {
        "success": True,
        "research": (
            "## 调研报告：" + topic + "\n\n"
            "### 主题概述\n" + topic + "是跨境支付行业当前最受关注的话题之一。\n\n"
            "### 目标受众\n- 跨境电商卖家（年营收50-500万）\n- 外贸企业财务负责人\n- 独立站卖家\n\n"
            "### 热点角度\n1. 政策变化带来的新机遇\n2. 费率对比：省钱就是赚钱\n3. 真实案例分享\n\n"
            "### 关键数据\n- 东南亚电商市场2026年预计突破3000亿美元\n- 跨境收款费率行业均值0.3%-1%\n"
        ),
        "draft": (
            "# " + topic + "：跨境卖家必须知道的3件事\n\n"
            "你还在为高额的跨境收款手续费发愁吗？\n\n"
            "据最新数据显示，东南亚电商市场2026年将突破3000亿美元，但很多卖家却因为选错收款渠道，"
            "每年白白多付数万元手续费...\n\n"
            "## 第一件事：费率是可以谈的\n很多卖家不知道，跨境收款的费率其实有很大差异...\n\n"
            "## 第二件事：本地牌照=安全保障\n没有本地支付牌照的服务商，资金安全是最大风险...\n\n"
            "## 第三件事：到账速度决定现金流\nT+1到账和T+3到账，一个月下来差的可不是2天...\n\n"
            "如果你也在找更好的东南亚收款方案，欢迎了解Ksher——8国本地牌照，费率0.05%起。"
        ),
        "edited": (
            "# " + topic + "：90%跨境卖家不知道的3个省钱秘诀\n\n"
            "每年多付3-5万收款手续费？不是你赚得少，是选错了渠道。\n\n"
            "2026年东南亚电商市场突破3000亿美元，但收款费率差距最高可达20倍——\n"
            "有人付0.05%，有人付1%。差别在哪？\n\n"
            "**秘诀一：费率不是固定的，选对服务商能省80%**\n"
            "行业均值0.3%-1%，但本地化服务商（如Ksher）可做到0.05%起...\n\n"
            "**秘诀二：本地牌照 = 资金安全底线**\n"
            "没有本地牌照的平台，你的钱走的是\"灰色通道\"...\n\n"
            "**秘诀三：T+1到账，现金流多转一圈**\n"
            "同样100万月流水，T+1比T+5每月多赚利息2000+...\n\n"
            "📌 Ksher：8国本地牌照 | 费率0.05%起 | T+1到账\n想聊聊？私信我。"
        ),
        "adapted": (
            "---\n\n"
            "【朋友圈版】\n\n"
            "做东南亚跨境的朋友注意了 ⚠️\n\n"
            "你的收款费率是多少？行业里有人付1%，有人只付0.05%，差20倍！\n\n"
            "3个省钱要点：\n"
            "1⃣ 选本地牌照服务商，费率最低\n"
            "2⃣ T+1到账，现金流更健康\n"
            "3⃣ 8国牌照=资金安全保障\n\n"
            "感兴趣的扣1，私聊详解 👇\n\n"
            "---\n\n"
            "【公众号版】\n\n"
            "（保留完整文章结构，此处省略...）\n\n"
            "---\n\n"
            "【小红书版】\n\n"
            "🔥 跨境卖家必看！省钱秘诀大公开 💰\n\n"
            "姐妹们/兄弟们！做跨境电商的一定要看这篇！\n\n"
            "我之前收款一直用XX，费率1%\n后来换了Ksher，费率直接降到0.05%！\n"
            "一年省了好几万 😱\n\n"
            "#跨境电商 #东南亚电商 #跨境收款 #省钱攻略"
        ),
        "error": "",
    }


def mock_competitive_analysis(competitor_name: str) -> dict:
    """Mock竞品分析结果"""
    cn = competitor_name
    return {
        "success": True,
        "posts_summary": "共收集到 " + cn + " 在5个平台的15条社交媒体内容。",
        "analysis": (
            "## " + cn + " 内容策略分析\n\n"
            "### 内容策略\n"
            "- 主要发布：行业资讯(40%)、客户案例(30%)、产品功能介绍(20%)、活动推广(10%)\n"
            "- 发布频率：朋友圈每天1-2条，公众号每周2-3篇\n\n"
            "### 受众定位\n"
            "- 主攻中小跨境电商卖家，年营收100-1000万\n"
            "- 内容偏实操导向，强调\"省钱\"\"便捷\"\n\n"
            "### 优势卖点\n"
            "- 反复强调：低费率、快到账、一站式服务\n"
            "- 弱化提及：牌照合规、资金安全\n\n"
            "### 薄弱环节\n"
            "- 东南亚本地化内容较少\n"
            "- 缺少深度技术解读类内容\n"
            "- 客户证言真实感不足"
        ),
        "report": (
            "# " + cn + " 竞品内容分析报告\n\n"
            "## 1. 执行摘要\n"
            + cn + "的内容策略以高频发布+低门槛获客为主，"
            "在费率和便捷性上投入大量内容资源，但在合规和安全方面的差异化内容不足。"
            "这为Ksher提供了明确的差异化机会。\n\n"
            "## 2. 内容策略矩阵\n"
            "| 维度 | " + cn + " | Ksher机会 |\n"
            "|------|---------|--------|\n"
            "| 内容类型 | 资讯+案例为主 | 深度分析+合规解读 |\n"
            "| 发布频率 | 高频（日更） | 精品路线（周3-4篇） |\n"
            "| 受众定位 | 中小卖家 | 中大型企业 |\n"
            "| 核心卖点 | 低费率 | 合规+安全+本地化 |\n\n"
            "## 3. 行动建议\n"
            "1. **打合规牌**：发布东南亚各国支付牌照科普系列\n"
            "2. **做深度内容**：每月1篇行业白皮书\n"
            "3. **强化案例**：收集真实客户视频证言\n"
            "4. **差异化视觉**：建立统一的品牌视觉体系\n"
            "5. **互动营销**：举办线上直播/问答活动"
        ),
        "error": "",
    }
