# 终端2启动指令 — 前端工程师+UI设计师

## 角色定位

你是 Ksher AgentAI 项目的前端工程师和 UI 设计师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 文件管辖范围

- **负责**：`ui/` `app.py` `assets/`
- **只读参考**：`config.py`（品牌色配置）`docs/INTERFACES.md`（接口约定）
- **不碰**：`agents/` `services/` `orchestrator/` `knowledge/` `prompts/`

## 技术栈

- Streamlit（页面框架）
- CSS（品牌主题注入，通过 st.markdown unsafe_allow_html）
- Plotly（图表）
- python-pptx（PPT生成，待实现）

## 品牌色（从 config.py 读取）

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

## 当前项目状态

Day 3 完成 85%，核心功能（一键备战）已跑通真实LLM。

**已有页面**：
- ✅ `ui/pages/battle_station.py` — 一键备战（Mock+真实双模式）
- ✅ `ui/pages/content_factory.py` — 内容工厂（4场景内容生成）
- ✅ `ui/pages/knowledge_qa.py` — 知识问答（5类问题回答）
- ⬜ `ui/pages/objection_sim.py` — 异议模拟（占位符，PM在另一终端实现）
- ⬜ `ui/pages/design_studio.py` — 海报/PPT（占位符，PM在另一终端实现）
- ⬜ `ui/pages/dashboard.py` — 仪表盘（未创建）

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

2. **添加动画过渡**
   - 按钮 hover：transform translateY(-1px) + box-shadow
   - Tab 切换：0.2s ease 过渡
   - 卡片展开：0.3s ease

3. **优化滚动条**
   - 已配置，检查是否在各浏览器一致

4. **输入框聚焦状态**
   - 聚焦时边框变为 primary 色
   - 添加微妙的 glow 效果

### P1：响应式布局

当前布局在宽屏下正常，但需要：
1. 检查移动端（<768px）下的表现
2. 侧边栏在窄屏下自动收起
3. 表单字段在窄屏下单列排列

### P2：错误处理UI

当前只有基础的 st.error/st.warning，需要统一：
1. 网络断开提示（API调用失败时的友好提示）
2. API额度不足提示
3. 加载状态统一（spinner样式）

### P3：各页面视觉一致性检查

检查这3个已有页面的视觉一致性：
- `battle_station.py` — 一键备战
- `content_factory.py` — 内容工厂
- `knowledge_qa.py` — 知识问答

确保：
- 标题样式一致（字号/颜色/间距）
- 按钮样式一致
- 卡片/容器背景色一致
- 分割线样式一致

## 协同规则

1. **PM在另一终端工作**，可能会修改 `ui/pages/objection_sim.py` 和 `ui/pages/design_studio.py`，你不要碰这两个文件。
2. **如果你发现需要修改 app.py 中的路由**（比如新增页面导入），可以修改，但只改路由部分，不动其他逻辑。
3. **CSS 修改集中在 app.py 的 `_inject_brand_css()` 函数**。
4. **每天结束时**，在 `DEVLOG.md` 追加你的产出记录。

## 遇到问题

- 阻塞问题 → 立即停下来说明，不要跳过
- 需要接口信息 → 读 `docs/INTERFACES.md`
- 需要品牌色 → 读 `config.py`

## 启动后先做什么

1. 读 `app.py` 了解当前CSS注入逻辑
2. 读 `ui/pages/battle_station.py` 了解页面结构
3. 启动 `streamlit run app.py` 在浏览器中查看当前效果
4. 制定美化计划，按P0→P1→P2→P3顺序执行
