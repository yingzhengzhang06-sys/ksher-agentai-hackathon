# 终端2启动指令 — Day 5 联调部署

## 角色定位

你是 Ksher AgentAI 项目的前端工程师和 UI 设计师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 当前状态（Day 4 完成，进入 Day 5）

**Day 4 已完成**：
- ✅ 6个页面全部可用（一键备战/内容工厂/知识问答/异议模拟/海报PPT/仪表盘）
- ✅ CSS美化完成（变量系统/动画/响应式/Metric美化）
- ✅ error_handlers 集成到5个页面
- ✅ dashboard Plotly图表完整（漏斗/饼图/柱状图/折线）
- ✅ Git提交：deploy readiness + error_handlers集成 + ProposalAgent修复

**Day 5 目标**：Streamlit Cloud 部署上线 + 演示可用性验证

---

## 你的任务

### P0：Streamlit Cloud 部署

1. **准备部署文件**
   - 确认 `requirements.txt` 包含所有依赖（streamlit/plotly/pandas/openai/anthropic/python-dotenv）
   - 确认 `.gitignore` 正确排除了 `.env` 和敏感文件
   - 确认 `README.md` 有项目描述（Streamlit Cloud会显示）

2. **创建 GitHub 仓库（如尚未创建）**
   ```bash
   cd /Users/macbookm4/Desktop/黑客松参赛项目
   git init  # 如果还没初始化
   git add .
   git commit -m "Day 5: deploy to Streamlit Cloud"
   # 推送到 GitHub
   ```

3. **Streamlit Cloud 部署步骤**
   - 访问 https://share.streamlit.io/
   - 用 GitHub 账号登录
   - 选择仓库：`yingzhengzhang06-sys/ksher-agentai-hackathon`（或你的仓库名）
   - 主文件路径填：`app.py`
   - 点击 Deploy
   - 等待部署完成（通常2-3分钟）

4. **部署后验证**
   - 获取公开URL（类似 https://xxx.streamlit.app）
   - 在无痕模式下打开URL，确认无需登录即可访问
   - 测试6个页面切换正常
   - 测试一键备战Mock模式可生成作战包

5. **环境变量配置（在Streamlit Cloud后台）**
   - 进入 App Settings → Secrets
   - 添加以下环境变量：
     ```toml
     KIMI_API_KEY = "sk-FN1rYbMNWVwSGQc1Jrd3Sd4GQ2dnqcv7L9bGzXMhsRyL0hv6"
     KIMI_BASE_URL = "https://api.moonshot.cn/v1"
     ANTHROPIC_API_KEY = "sk-H1NeRZj569mvo7beH5RB7IZjGF4usIwZ8saWpP83H4eIm8Pe"
     ANTHROPIC_BASE_URL = "https://open.cherryin.ai/v1"
     ```
   - 保存后重新部署

### P1：演示可用性检查

6. **双战场演示场景验证**

   场景A（银行客户）：
   - 输入：深圳外贸工厂 / B2B / 泰国 / 月流水80万 / 银行电汇 / 痛点：手续费高、到账慢
   - 检查：战场类型显示"增量战场"、话术强调隐性成本

   场景B（竞品客户）：
   - 输入：义乌Shopee卖家 / B2C / 泰国 / 月流水30万 / PingPong / 痛点：多平台管理麻烦
   - 检查：战场类型显示"存量战场"、话术强调本地牌照+锁汇

7. **移动端适配检查**
   - 用手机或浏览器开发者工具（iPhone 375px宽度）
   - 检查：侧边栏可收起、表单字段单列排列、一键备战4Tab可横向滚动

8. **网络断开降级测试**
   - 在生成作战包时断开WiFi
   - 检查：是否显示品牌风格的错误提示（render_mock_fallback_notice）
   - 检查：是否自动回退到Mock模式

### P2：性能优化（可选）

9. **加载速度优化**
   - 检查首次加载时间（目标 < 3秒）
   - 如果慢：检查是否有大文件加载，考虑延迟加载Plotly

10. **缓存验证**
    - 同一客户画像生成两次作战包
    - 第二次应该更快（ResultCache命中）

---

## 产出物

完成以下产出后，在 DEVLOG.md 追加记录：

| # | 产出 | 说明 |
|---|------|------|
| 5.1 | Streamlit Cloud URL | 公开可访问的Demo地址 |
| 5.2 | 部署截图 | Streamlit Cloud后台部署成功截图 |
| 5.3 | 演示检查清单 | 双战场场景验证结果 |
| 5.4 | 移动端截图 | iPhone宽度下的页面截图 |

---

## 阻塞处理

- **部署失败** → 检查requirements.txt是否完整、检查.gitignore是否排除了.env
- **API Key不生效** → 检查Streamlit Cloud Secrets设置格式（必须是TOML格式）
- **页面加载慢** → 检查是否有大文件（如logo.png过大）
- **任何阻塞** → 立即停下来说明，不要跳过

---

## 启动后先做什么

1. 检查当前Git状态：`git status`
2. 确认requirements.txt完整：`cat requirements.txt`
3. 开始P0部署步骤
4. 每完成一步，在浏览器中验证

---

## 附：requirements.txt 参考内容

确保包含以下依赖：

```
streamlit>=1.32.0
plotly>=5.18.0
pandas>=2.0.0
openai>=1.12.0
anthropic>=0.18.0
python-dotenv>=1.0.0
Pillow>=10.0.0
python-pptx>=0.6.23
```
