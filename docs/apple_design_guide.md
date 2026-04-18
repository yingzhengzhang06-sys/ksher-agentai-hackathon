# Ksher AgentAI — Apple 风格设计规范

> 参照苹果官网设计语言，为项目注入极简、留白、高级的视觉体验。

---

## 设计哲学

| 原则 | 说明 |
|------|------|
| **留白至上** | 大量留白让内容呼吸，不堆砌信息 |
| **内容优先** | 视觉服务于内容，不喧宾夺主 |
| **微妙反馈** | 动效克制、优雅，不刺眼 |
| **一致性** | 全站色彩、字体、间距统一 |

---

## 色彩系统

### 主色

| Token | 值 | 用途 |
|-------|-----|------|
| `primary` | `#E83E4C` | 品牌红，CTA按钮、重点标识 |
| `primary_dark` | `#C52D3A` | 按钮悬停态 |
| `primary_light` | `#FF6B76` | 浅色强调 |

### 中性色（Apple 灰度）

| Token | 值 | 用途 |
|-------|-----|------|
| `background` | `#FFFFFF` | 页面背景 |
| `surface` | `#F5F5F7` | 卡片/侧边栏背景（Apple Gray） |
| `surface_hover` | `#EBEBF0` | 卡片悬停态 |
| `text_primary` | `#1D1D1F` | 主标题、正文 |
| `text_secondary` | `#86868B` | 副标题、描述 |
| `text_muted` | `#A1A1A6` | 辅助文字、时间戳 |
| `border` | `#D2D2D7` | 输入框边框 |
| `border_light` | `#E8E8ED` | 分隔线、卡片边框 |

### 功能色

| Token | 值 | 用途 |
|-------|-----|------|
| `success` | `#00C9A7` | 成功状态 |
| `warning` | `#FFB800` | 警告状态 |
| `danger` | `#E83E4C` | 错误状态 |

---

## 排版

### 字号层级

| 层级 | 大小 | 字重 | 字距 | 用途 |
|------|------|------|------|------|
| H1 | 2rem+ | 700 | -0.03em | 页面大标题 |
| H2 | 1.5rem | 600 | -0.02em | 区块标题 |
| H3 | 1.2rem | 600 | -0.01em | 子标题 |
| Body | 1rem | 400 | normal | 正文 |
| Caption | 0.85rem | 400 | normal | 辅助说明 |

### 字体栈

Streamlit 默认使用系统字体栈（Inter/SF Pro/Helvetica），无需额外配置。

---

## 组件规范

### 按钮

**主按钮**
- 背景：`primary` (#E83E4C)
- 文字：白色
- 圆角：`9999px`（药丸形）
- 内边距：`0.55rem 1.5rem`
- 字重：500
- 悬停：opacity 0.92（无位移、无阴影）
- 点击：scale(0.97)

**次按钮**
- 背景：透明
- 文字：`primary`
- 边框：`1.5px solid primary`
- 圆角：`9999px`
- 悬停：`rgba(232,62,76,0.06)` 背景

### 输入框

- 背景：白色
- 文字：`#1D1D1F`
- 边框：`1px solid #D2D2D7`
- 圆角：`0.75rem`
- 聚焦：品牌色边框 + `0 0 0 4px rgba(232,62,76,0.1)` glow
- 悬停：边框 `#86868B`

### 卡片/容器

- 背景：`#F5F5F7`
- 无边框、无阴影
- 圆角：`1rem`
- 悬停：背景 `#EBEBF0`

### Tab

- 文字：`#86868B`（未选中）/ `#1D1D1F`（悬停）/ `#E83E4C`（选中）
- 无背景色变化
- 选中态：底部 `2px solid #E83E4C`

### 侧边栏

- 背景：`#F5F5F7`
- 右边框：`1px solid #E8E8ED`
- 导航项：深灰文字，悬停时品牌红
- 选中态：品牌红 + 浅红背景

---

## 间距

| 场景 | 值 |
|------|-----|
| 页面内边距 | `2.5rem 3rem` |
| 卡片内边距 | `1.25rem 1.5rem` |
| Section 间距 | `2rem+` |
| 组件间距 | `1rem` |

---

## 与深色主题的差异总结

| 维度 | Apple 浅色（当前） | 原深色主题 |
|------|-------------------|-----------|
| 背景 | `#FFFFFF` | `#0F0F1A` |
| 卡片 | `#F5F5F7`，无阴影 | `#1E1E2F`，有阴影 |
| 文字 | `#1D1D1F` | `#FFFFFF` |
| 按钮 | 药丸形，无阴影 | 直角圆角，有阴影 |
| 悬停 | opacity/背景变化 | translateY + shadow |
| 边框 | `#D2D2D7` 实色 | `rgba(255,255,255,0.1)` |
| 分隔线 | `#E8E8ED` | `rgba(255,255,255,0.08)` |

---

## 参考

- [Apple Design Resources](https://developer.apple.com/design/resources/)
- [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
