# ProposalAgent 修复方案（终端1）

## 问题现象

E2E 测试显示，ProposalAgent 生成的 8 个字段中，7 个字段只有 50-70 字，严重不符合每个章节 200 字以上的强制要求：

| 字段 | 当前字数 | 状态 |
|------|---------|------|
| industry_insight | 67 | ❌ 过短（默认值） |
| pain_diagnosis | 66 | ❌ 过短（默认值） |
| solution | 71 | ❌ 过短（默认值） |
| product_recommendation | 50 | ❌ 过短（默认值） |
| fee_advantage | 64 | ❌ 过短（默认值） |
| compliance | 56 | ❌ 过短（默认值） |
| onboarding_flow | 68 | ❌ 过短（默认值） |
| next_steps | 598 | ✅ 正常 |

## Root Cause（根因分析，已确认）

### 原因1：User Message JSON 模板值的实例文本太短

`agents/proposal_agent.py` 第 122-129 行的 `build_user_message()` 方法中，JSON 模板示例值只有 10-28 字：

```python
f'  "industry_insight": "基于 {INDUSTRY_OPTIONS.get(industry, industry)} 的行业趋势和挑战",',
f'  "pain_diagnosis": "针对客户使用 {current_channel} 的具体痛点诊断",',
f'  "solution": "Ksher 如何解决每个痛点",',
f'  "product_recommendation": "根据 {COUNTRY_OPTIONS.get(target_country, target_country)} 推荐最适合的产品组合",',
f'  "fee_advantage": "引用成本数据：切换到 Ksher，年省 ¥{annual_saving:,.0f}",',
f'  "compliance": "Ksher 在 {COUNTRY_OPTIONS.get(target_country, target_country)} 的合规保障",',
f'  "onboarding_flow": "从签约到收款的完整流程",',
f'  "next_steps": "明确的下一步行动 CTA"',
```

**Claude 的模仿行为**：LLM 会模仿 user message 中提供的示例格式和长度。当模板值只有 10-20 字时，即使 system prompt 要求每个章节 200 字，Claude 仍会倾向于生成与示例等长的内容。

### 原因2：`_parse_text_response` 提取失败

当 Claude 的输出被 markdown 代码块包裹时，正则表达式无法正确匹配大多数字段，导致大部分内容丢失，只能 fall back 到 `_fill_defaults()` 中的 50-70 字默认值。

## 修复方案

### 修复1：修改 JSON 模板示例值（必须）

将第 122-129 行的每个 JSON 模板值替换为 200 字以上的占位文本，不要只用 "..." 省略，而是写满完整的段落示例。**这是最关键的一步。**

**修改前（第122行）：**
```python
f'  "industry_insight": "基于 {INDUSTRY_OPTIONS.get(industry, industry)} 的行业趋势和挑战",',
```

**修改后（第122行）：**
```python
f'  "industry_insight": "此处应写一段至少 200 字的行业洞察分析。包括：(1) 行业规模与增长趋势——引用权威数据说明市场有多大、增速如何；(2) 竞争格局变化——主要市场参与者、消费者行为变化、政策环境影响；(3) 跨境收款的核心挑战——为什么传统方案已无法满足该行业的发展需求；以及对客户意味着什么——这些趋势如何影响客户的利润空间和竞争力。不要只列数字，要有逻辑递进和深度洞察。",',
```

其余 7 个字段同理，每个模板值都必须达到 200 字以上。下面提供每个字段的占位文本模板：

---

**industry_insight（第122行）：**
```python
f'  "industry_insight": "此处应写一段至少 200 字的行业洞察分析。包括：(1) 行业规模与增长趋势——引用权威数据说明市场有多大、增速如何；(2) 竞争格局变化——主要市场参与者、消费者行为变化、政策环境影响；(3) 跨境收款的核心挑战——为什么传统方案已无法满足该行业的发展需求；以及对客户意味着什么——这些趋势如何影响客户的利润空间和竞争力。不要只列数字，要有逻辑递进和深度洞察。",',
```

**pain_diagnosis（第123行）：**
```python
f'  "pain_diagnosis": "此处应写一段至少 200 字的痛点诊断。不要只说\"手续费高\"，要具体到三个层次：第一，显性成本具体是多少——当前渠道的费率结构如何构成，每月固定费用和比例费用分别是多少；第二，隐性成本有哪些——汇率损失、资金占用时间、多平台管理的人工成本；第三，业务影响是什么——这些成本如何拖累客户的备货能力、定价竞争力和资金周转效率。每个痛点都要有数据和逻辑链条。",',
```

**solution（第124行）：**
```python
f'  "solution": "此处应写一段至少 200 字的解决方案描述。不是简单地列出产品功能，而是针对上述每个痛点给出完整的解决方案逻辑：针对手续费高的痛点——Ksher 的费率结构和节省方式是什么，具体能降低多少百分比；针对汇率损失的痛点——Ksher 采用的汇率机制和与国际市价的对比优势；针对到账慢的问题——T+1 到账如何释放资金占用成本、提高资金周转率；针对多平台管理问题——一站式收款如何降低人力成本。每个解决方案都要有量化价值和业务逻辑支撑。",',
```

**product_recommendation（第125行）：**
```python
f'  "product_recommendation": "此处应写一段至少 200 字的产品推荐。基于客户的目标国家和业务类型，推荐最适合的 Ksher 产品组合。包括：(1) 主推产品——为什么这个产品最匹配客户的业务场景，具体有哪些功能；(2) 辅助产品——还可以搭配哪些增值服务，如多币种账户、自动结算、API 对接等；(3) 与竞品对比——为什么 Ksher 的产品在该市场上具有差异化优势；(4) 客户收益预期——使用这些产品后预计能达到什么效果。",',
```

**fee_advantage（第126行）：**
```python
f'  "fee_advantage": "此处应写一段至少 200 字的费率优势分析。引用 CostAgent 提供的具体成本数据：年度总成本对比、各项成本的明细拆解（手续费、汇率损失、资金时间成本、多平台管理成本、合规风险成本），以及切换到 Ksher 后的节省金额和节省比例。不要只罗列表格数字，要解释这些节省对客户业务的实际意义——省下的钱可以用来做什么，如何转为客户的核心竞争力。",',
```

**compliance（第127行）：**
```python
f'  "compliance": "此处应写一段至少 200 字的合规保障说明。详细介绍 Ksher 在目标国家的合规资质：持有哪些监管机构颁发的牌照、牌照类型和覆盖范围、监管框架下的资金安全保障机制、合规审计和风控体系。同时说明合规对客户的价值：降低交易冻结风险、满足跨境收付的法规要求、避免无资质服务商的潜在损失。用客户能理解的商业语言，不要变成法律条文罗列。",',
```

**onboarding_flow（第128行）：**
```python
f'  "onboarding_flow": "此处应写一段至少 200 字的接入流程说明。详细描述从签约到成功收款的完整流程：(1) 申请阶段——需要提交哪些资料、资料准备周期是多久；(2) 审核阶段——Ksher 合规团队的审核流程和时间承诺；(3) 技术对接——是否需要技术人员参与、集成方式有哪些选择；(4) 测试上线——测试环境验证、首笔收款确认；(5) 后续支持——专属客户经理的持续服务机制。让客户感到门槛低、流程清晰、有专人支持。",',
```

**next_steps（第129行）：**
```python
f'  "next_steps": "此处应写一段至少 200 字的下一步行动方案。给出三个明确可执行的行动步骤，每个步骤都包含：(1) 具体做什么——\"安排 30 分钟线上沟通\"而不是\"我们开始吧\"；(2) 何时完成——给出明确的时间框架；(3) 谁来负责——说明 Ksher 会提供哪些支持资源；(4) 预期产出——这步完成后能达到什么效果。整体语气要积极但不催促，让客户感受到是在帮助他们做出更好的决策，而不是推销压力。",',
```

### 修复2：改进 `_parse_text_response`（建议）

当前正则表达式无法正确处理 markdown 代码块包裹的 JSON。建议改进：

```python
def _parse_text_response(self, text: str, context: dict) -> dict:
    """回退解析：优先提取 markdown 代码块中的 JSON，再按章节标题提取"""
    result = {key: "" for key in [
        "industry_insight", "pain_diagnosis", "solution",
        "product_recommendation", "fee_advantage", "compliance",
        "onboarding_flow", "next_steps",
    ]}

    # 首先尝试提取 markdown 代码块中的 JSON
    import re, json
    json_block_match = re.search(
        r'```(?:json)?\s*\n?(.*?)\n?```',
        text, re.DOTALL
    )
    if json_block_match:
        try:
            parsed = json.loads(json_block_match.group(1).strip())
            for key in result:
                if key in parsed:
                    result[key] = parsed[key]
            # 如果至少 extract 到 5 个字段，直接返回
            if sum(1 for v in result.values() if v) >= 5:
                return result
        except json.JSONDecodeError:
            pass  # fallback to regex extraction

    # 保持原有的正则提取逻辑...
```

### 修复3：增加最小字数验证（可选）

在 `_validate_output` 中增加最小字数检查：

```python
def _validate_output(self, parsed: dict) -> bool:
    required = ["industry_insight", "pain_diagnosis", "solution",
                "product_recommendation", "fee_advantage", "compliance",
                "onboarding_flow", "next_steps"]
    if not all(k in parsed and parsed[k] for k in required):
        return False
    # 新增：每个字段至少 150 字（留出 margin）
    MIN_LENGTH = 150
    for key in required:
        if len(str(parsed[key])) < MIN_LENGTH:
            return False
    return True
```

## 验证方法

修改后运行以下测试：
```bash
cd /Users/macbookm4/Desktop/黑客松参赛项目
python tests/test_e2e_real_llm.py
```

通过标准：8 个字段每个都 ≥150 字，且不是 `_fill_defaults()` 的内容。

## 优先级

| 修复 | 优先级 | 工作量 |
|------|-------|-------|
| 修复1：JSON 模板示例值 | P0（必须） | 5 分钟 |
| 修复2：改进解析逻辑 | P1（建议） | 10 分钟 |
| 修复3：最小字数验证 | P1（建议） | 5 分钟 |
