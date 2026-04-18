# Ksher AgentAI — 接口约定文档 (INTERFACES.md)

> **所有终端必须遵守此文档。Day 1 上午产出，下午并行开发的契约。**

---

## 1. LLMClient 接口

```python
# services/llm_client.py
class LLMClient:
    def stream_text(self, agent_name: str, system: str, user_msg: str,
                    temperature: float = 0.7):
        """
        统一流式输出接口：yield纯文本chunk，调用方无需关心底层SDK差异。

        Args:
            agent_name: "speech" | "cost" | "proposal" | "objection" |
                       "content" | "knowledge" | "design"
            system: System Prompt（含知识库注入内容）
            user_msg: 用户输入消息
            temperature: 温度参数

        Yields:
            str: 纯文本chunk
        """

    def call_sync(self, agent_name: str, system: str, user_msg: str,
                  temperature: float = 0.7) -> str:
        """
        同步调用（非流式），返回完整文本。
        用于CostAgent等需要完整结果后再传递给下游Agent的场景。
        """
```

---

## 2. KnowledgeLoader 接口

```python
# services/knowledge_loader.py
class KnowledgeLoader:
    def load(self, agent_name: str, context: dict) -> str:
        """
        按Agent名+客户上下文，选择性加载知识库文件，拼接为文本。

        Args:
            agent_name: Agent名称（speech/cost/proposal/objection/content/knowledge/design）
            context: {
                "industry": str,           # "b2c" | "b2b" | "service"
                "target_country": str,     # "thailand" | "malaysia" | ...
                "current_channel": str,    # 客户当前收款渠道
                ...
            }

        Returns:
            str: 拼接后的知识库文本
        """
```

---

## 3. BaseAgent 接口

```python
# agents/base_agent.py
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    temperature: float = 0.7

    def __init__(self, llm_client, knowledge_loader):
        self.llm_client = llm_client
        self.knowledge_loader = knowledge_loader

    @abstractmethod
    def generate(self, context: dict) -> dict:
        """同步生成，返回结构化结果dict。"""
        pass

    def stream(self, context: dict):
        """流式生成，yield文本chunk（UI直接消费）。"""
        pass

    @abstractmethod
    def build_system_prompt(self, knowledge: str) -> str:
        pass

    @abstractmethod
    def build_user_message(self, context: dict) -> str:
        pass
```

---

## 4. 各Agent输出格式约定

### SpeechAgent
```python
SpeechAgent.generate(context) -> {
    "elevator_pitch": str,      # 30秒电梯话术
    "full_talk": str,           # 3分钟完整讲解（分3段）
    "wechat_followup": str,     # 微信跟进话术（首次添加+后续）
    "battlefield": str          # 战场类型（increment/stock/education）
}
```

### CostAgent
```python
CostAgent.generate(context) -> {
    "comparison_table": {
        "ksher": {"fee": float, "fx_loss": float, "time_cost": float,
                  "mgmt_cost": float, "compliance_cost": float, "total": float},
        "current": {"fee": float, "fx_loss": float, "time_cost": float,
                    "mgmt_cost": float, "compliance_cost": float, "total": float}
    },
    "annual_saving": float,     # 年节省金额（元）
    "chart_data": dict,         # Plotly图表数据
    "summary": str              # AI解读话术
}
```

### ProposalAgent
```python
ProposalAgent.generate(context) -> {
    "industry_insight": str,
    "pain_diagnosis": str,
    "solution": str,
    "product_recommendation": str,
    "fee_advantage": str,
    "compliance": str,
    "onboarding_flow": str,
    "next_steps": str
}
```

### ObjectionAgent
```python
ObjectionAgent.generate(context) -> {
    "top_objections": [
        {
            "objection": str,
            "direct_response": str,
            "empathy_response": str,
            "data_response": str
        }
    ],
    "battlefield_tips": str
}
```

### ContentAgent
```python
ContentAgent.generate(context) -> {
    "content_type": str,
    "contents": [
        {
            "day": int,
            "title": str,
            "body": str,
            "image_suggestion": str,
            "publish_time": str,
            "category": str
        }
    ]
}
```

### KnowledgeAgent
```python
KnowledgeAgent.generate(context) -> {
    "answer": str,
    "ksher_advantages": [str],
    "speech_tip": str,
    "sources": [str],
    "confidence": str
}
```

### DesignAgent
```python
DesignAgent.generate(context) -> {
    "design_type": str,
    "headline": str,
    "subheadline": str,
    "selling_points": [str],
    "cta": str,
    "color_scheme": str,
    "layout_suggestion": str,
    "ppt_slides": [{"title": str, "content": str, "notes": str}]
}
```

---

## 5. Orchestrator 接口

```python
# orchestrator/agent_dispatcher.py
def generate_battle_pack(context: dict, agents: dict) -> dict:
    """
    两阶段半并行执行：
    阶段1：Speech + Cost + Objection 并行（3个Agent互不依赖）
    阶段2：Proposal 串行（依赖Cost的输出）

    Args:
        context: 客户画像 + 战场判断结果
        agents: {"speech": SpeechAgent, "cost": CostAgent, ...}

    Returns:
        dict: {"speech": {}, "cost": {}, "proposal": {}, "objection": {}}
    """
```

---

## 6. UI 组件接口

```python
# ui/components/customer_input_form.py
def render_customer_input_form() -> dict:
    """
    渲染客户信息输入表单。
    Returns: {
        "company": str, "industry": str, "target_country": str,
        "monthly_volume": float, "current_channel": str, "pain_points": [str]
    }
    """

# ui/components/battle_pack_display.py
def render_battle_pack(pack: dict):
    """
    渲染作战包输出（4个Tab：话术/成本/方案/异议）。
    接收 generate_battle_pack() 的返回结果。
    """

# ui/components/sidebar.py
def render_sidebar():
    """
    渲染侧边栏导航。
    页面：一键备战 | 内容工厂 | 知识问答 | 异议模拟 | 海报/PPT | 仪表盘
    """
```

---

## 7. 知识库文件规范

- 文件格式：纯Markdown，无Obsidian语法（无[[双链]]、无YAML frontmatter）
- 每文件上限：3000字（超出则精简）
- 目录结构：
  ```
  knowledge/
  ├── index.json          # 索引文件
  ├── base/               # 基础知识（8篇）
  ├── b2c/                # B2C各国（5篇）
  ├── b2b/                # B2B各国（6篇）
  ├── service_trade/      # 服务贸易（5篇）
  ├── products/           # 特色产品（2篇）
  ├── competitors/        # 竞品分析（7篇）
  ├── operations/         # 操作+FAQ（2篇）
  ├── strategy/           # 行业方案+优势策略（2篇）
  └── fee_structure.json  # 费率参数
  ```

---

## 8. Session State 规范

```python
# Streamlit session_state 约定
st.session_state.customer_context = {
    "company": str,
    "industry": str,        # "b2c" | "b2b" | "service"
    "target_country": str,
    "monthly_volume": float,
    "current_channel": str,
    "pain_points": [str],
    "battlefield": str       # "increment" | "stock" | "education"
}

st.session_state.battle_pack = {
    "speech": dict,
    "cost": dict,
    "proposal": dict,
    "objection": dict,
    "generated_at": datetime
}
```

---

*文档版本：v1.0*
*创建时间：Day 1 上午*
*所有终端以此为准，接口变更需经终端4（PM）确认*
