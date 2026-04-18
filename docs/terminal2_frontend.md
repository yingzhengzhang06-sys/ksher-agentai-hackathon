# 终端2启动指令 — 前端工程师+UI设计师

## 角色定位

你是 Ksher AgentAI 项目的前端工程师和 UI 设计师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 文件管辖范围

- **负责**：`ui/` `app.py`（仅CSS和路由部分） `assets/`
- **只读参考**：`config.py`（品牌色）`docs/INTERFACES.md`（接口约定）
- **不碰**：`agents/` `services/` `orchestrator/` `knowledge/` `prompts/`

## 技术栈

- Streamlit（页面框架）
- CSS（品牌主题注入，通过 st.markdown unsafe_allow_html）
- Plotly（图表）

## 品牌色（从 config.py 读取，不要修改）

```python
BRAND_COLORS = {
    "primary": "#E83E4C",       # Ksher红
    "primary_dark": "#C52D3A",
    "primary_light": "#FF6B76",
    "secondary": "#1A1A2E",
    "accent": "#00C9A7",        # 成功绿
    "background": "#0F0F1A",    # 全局背景
    "surface": "#1E1E2F",       # 卡片/面板背景
    "text_primary": "#FFFFFF",
    "text_secondary": "#B0B0C0",
    "text_muted": "#6B6B7B",
    "success": "#00C9A7",
    "warning": "#FFB800",
    "danger": "#E83E4C",
    "info": "#3B82F6",
}
```

## 当前项目状态（Day 3完成，进入Day 4）

**已有页面（已可用）**：
- ✅ `ui/pages/battle_station.py` — 一键备战（Mock+真实双模式）
- ✅ `ui/pages/content_factory.py` — 内容工厂（4场景内容生成）
- ✅ `ui/pages/knowledge_qa.py` — 知识问答（5类问题回答）
- ✅ `ui/pages/objection_sim.py` — 异议模拟（3种训练模式）
- ✅ `ui/pages/design_studio.py` — 海报/PPT（4主题海报+9页PPT大纲）
- ⬜ `ui/pages/dashboard.py` — 仪表盘（未创建，占位符）

**已有组件**：
- ✅ `ui/components/sidebar.py` — 侧边栏导航
- ✅ `ui/components/customer_input_form.py` — 客户输入表单
- ✅ `ui/components/battle_pack_display.py` — 作战包4Tab展示

**主入口**：
- ✅ `app.py` — Streamlit主入口 + 品牌CSS注入 + Session State + 页面路由

## 你的任务（按优先级排序）

### P0：全局CSS美化

当前 `app.py` 中的 `_inject_brand_css()` 已经注入了基础品牌色，但还有优化空间：

1. **统一间距系统**
   - 页面内边距：2rem top / 3rem bottom
   - 卡片间距：1rem
   - 组件间距：0.5rem
   - 确保所有页面一致

2. **添加动画过渡**
   - 按钮 hover：transform translateY(-1px) + box-shadow
   - Tab 切换：0.2s ease 过渡
   - 卡片展开：0.3s ease
   - 页面切换：淡入效果

3. **输入框聚焦状态**
   - 聚焦时边框变为 primary 色
   - 添加微妙的 glow 效果（box-shadow: 0 0 0 2px rgba(232,62,76,0.2)）

4. **优化 Metric 组件**
   - 成本Tab中的3个metric卡片加背景色和圆角
   - 数字放大，标签缩小

### P1：响应式布局

当前布局在宽屏下正常，需要：
1. 检查移动端（<768px）下的表现
2. 侧边栏在窄屏下自动收起（Streamlit原生支持，验证即可）
3. 表单字段在窄屏下单列排列
4. 作战包4Tab在窄屏下堆叠或横向滚动

### P2：错误处理UI

当前只有基础的 st.error/st.warning，需要统一：
1. **网络断开提示**：API调用失败时的友好提示（带重试按钮）
2. **API额度不足提示**：明确告诉用户联系管理员充值
3. **加载状态统一**：所有spinner样式一致，加品牌色
4. **空状态设计**：无数据时的友好提示（插画+文字）

### P3：仪表盘页面

创建 `ui/pages/dashboard.py`：
- 客户转化率漏斗（模拟数据）
- 各战场类型成交统计（饼图/柱状图）
- Agent生成内容使用统计（折线图）
- 本周/本月关键指标卡片
- 数据来源：`data/mock_dashboard.json`（终端1会提供）

### P4：各页面视觉一致性检查

检查这5个已有页面的视觉一致性：
- `battle_station.py` — 一键备战
- `content_factory.py` — 内容工厂
- `knowledge_qa.py` — 知识问答
- `objection_sim.py` — 异议模拟
- `design_studio.py` — 设计工作室

确保：标题样式一致、按钮样式一致、卡片背景色一致、分割线样式一致

## 协同规则

1. **终端1（后端）正在优化Agent输出质量** — 如果Agent输出格式变了，终端1会通知PM，PM会告诉你
2. **如果你发现需要修改 app.py 中的路由**（比如新增仪表盘页面导入），可以修改，但只改路由部分
3. **CSS 修改集中在 `app.py` 的 `_inject_brand_css()` 函数** — 不要分散到各个页面
4. **每天结束时**，在 `DEVLOG.md` 追加你的产出记录（只写你的部分）
5. **阻塞问题** → 立即停下来说明，不要跳过

## 启动后先做什么

1. 读 `app.py` 了解当前CSS注入逻辑
2. 启动 `streamlit run app.py` 在浏览器中查看当前效果
3. 制定美化计划，按 P0→P1→P2→P3→P4 顺序执行
4. 每完成一个任务，刷新浏览器验证效果
