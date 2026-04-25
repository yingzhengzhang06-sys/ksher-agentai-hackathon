# Ksher AgentAI 智能工作台 — 账号体系设计方案

> **方案选型**：B 方案（SQLite自研）
> **目标**：为系统引入账号注册/审核/管理全流程，支持渠道商自主注册和后台配号两种模式
> **状态**：待评审

---

## 1. 需求概述

### 1.1 当前状态

系统为纯 Streamlit SPA，无账号体系，任何人访问即可使用全部功能，数据存储在本地 JSON/SQLite 文件中。

### 1.2 目标状态

| 功能 | 说明 |
|------|------|
| **注册** | 渠道商/用户填写信息自主注册，提交后进入待审核状态 |
| **审核** | 管理员在后台查看注册申请，通过/拒绝 |
| **后台配号** | 管理员绕过注册流程，直接创建账号并分配密码给渠道商 |
| **登录** | 已审核通过的用户用账号密码登录 |
| **权限控制** | 不同角色看到不同的页面和功能 |
| **Session管理** | 登录态持久化（当前会话+可选7天Cookie） |
| **安全** | 密码bcrypt加密、登录日志审计 |

### 1.3 使用场景

```
场景A — 渠道商自主注册
  渠道商小王访问系统 → 点击"注册" → 填写账号/密码/昵称/渠道名 → 提交
  → 管理员收到待审核通知 → 审核通过 → 小王登录使用

场景B — 管理员后台配号
  管理员收到渠道商合作意向 → 后台"新增账号" → 填账号/密码/昵称 → 保存
  → 把账号密码发给渠道商 → 渠道商直接登录使用

场景C — 账号管理
  管理员后台查看所有账号 → 禁用离职员工 → 重置遗忘密码 → 查看登录日志
```

---

## 2. 数据库设计（SQLite）

### 2.1 users 表 — 用户主表

```sql
CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,           -- 登录账号（英文字母+数字）
    password_hash TEXT NOT NULL,                  -- bcrypt 加密后的密码
    nickname      TEXT,                           -- 显示名称（中文可）
    role          TEXT NOT NULL DEFAULT 'user',   -- admin / channel / user
    status        TEXT NOT NULL DEFAULT 'pending',-- pending / active / disabled
    channel_name  TEXT,                           -- 所属渠道商名称
    channel_code  TEXT,                           -- 渠道商编码（如 KSH-001）
    contact_phone TEXT,                           -- 联系电话（可选）
    contact_email TEXT,                           -- 联系邮箱（可选）
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by   INTEGER REFERENCES users(user_id),-- 审核人ID
    approved_at   TIMESTAMP,                      -- 审核通过时间
    last_login_at TIMESTAMP,                      -- 最后登录时间
    login_count   INTEGER DEFAULT 0               -- 累计登录次数
);
```

**索引**：
```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_channel ON users(channel_code);
```

### 2.2 login_logs 表 — 登录审计日志

```sql
CREATE TABLE login_logs (
    log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(user_id),
    username   TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    success    BOOLEAN NOT NULL,     -- 1=成功, 0=失败
    fail_reason TEXT,                -- 失败原因（密码错误/账号禁用/待审核）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 数据关系图

```
users (1) ──────< (N) login_logs
  │
  │ approved_by → users.user_id (自关联，审核人)
```

---

## 3. 角色与权限模型

### 3.1 角色定义

| 角色 | 标识 | 权限范围 |
|------|------|---------|
| **系统管理员** | `admin` | 全部页面 + 账号管理后台 + 系统配置 |
| **渠道管理员** | `channel` | 标准功能页面（一键备战/内容工厂/知识问答等），看不到其他渠道数据 |
| **普通用户** | `user` | 标准功能页面，无管理权限 |

### 3.2 页面权限矩阵

| 页面/功能 | admin | channel | user |
|-----------|-------|---------|------|
| 一键备战 | ✅ | ✅ | ✅ |
| 内容工厂 | ✅ | ✅ | ✅ |
| 知识问答 | ✅ | ✅ | ✅ |
| 异议模拟 | ✅ | ✅ | ✅ |
| 设计工作室 | ✅ | ✅ | ✅ |
| 仪表盘 | ✅ | ✅ | ✅ |
| 销售支持 | ✅ | ✅ | ✅ |
| 话术培训师 | ✅ | ✅ | ✅ |
| 数据分析师 | ✅ | ✅ | ✅ |
| 财务经理 | ✅ | ❌ | ❌ |
| 行政助手 | ✅ | ❌ | ❌ |
| **账号管理后台** | ✅ | ❌ | ❌ |
| **审核注册申请** | ✅ | ❌ | ❌ |

> 注：权限矩阵可在评审后调整。channel 和 user 的权限差异可根据业务需要合并。

---

## 4. 模块设计

### 4.1 模块清单

```
services/
  └── auth_service.py          # 认证服务层（注册/登录/审核/密码管理）
ui/
  ├── pages/
  │   ├── login.py             # 登录页
  │   ├── register.py          # 注册页
  │   └── admin/
  │       └── user_mgmt.py     # 管理员-账号管理后台
  └── components/
      └── auth_guard.py        # 登录态守卫组件（未登录拦截）
config.py                      # 增加 AUTH_DB_PATH 配置
data/
  └── auth.db                  # SQLite 数据库文件（.gitignore 已忽略）
```

### 4.2 auth_service.py — 核心接口

```python
class AuthService:
    """认证服务：注册/登录/审核/账号管理"""

    # ---------- 注册 ----------
    def register(username, password, nickname, channel_name="",
                 channel_code="", contact_phone="", contact_email="") -> dict
        """用户自主注册，返回 {"success": True, "user_id": int}
            或 {"success": False, "error": str}"""

    # ---------- 登录 ----------
    def login(username, password, ip_address="", user_agent="") -> dict
        """验证账号密码，返回 {"success": True, "user": dict}
            或 {"success": False, "error": str}"""

    def logout(user_id: int) -> None
        """记录登出时间（可选）"""

    # ---------- 审核 ----------
    def approve_user(user_id: int, admin_id: int) -> bool
        """管理员审核通过"""

    def reject_user(user_id: int, admin_id: int, reason: str = "") -> bool
        """管理员拒绝注册"""

    # ---------- 账号管理（仅admin）----------
    def create_user_by_admin(username, password, nickname, role="user",
                             channel_name="", channel_code="") -> dict
        """管理员直接创建账号（后台配号），无需审核，状态直接为 active"""

    def list_users(status=None, role=None, channel_code=None) -> list
        """按条件筛选用户列表"""

    def list_pending_users() -> list
        """获取待审核列表"""

    def disable_user(user_id: int) -> bool
        """禁用账号"""

    def enable_user(user_id: int) -> bool
        """启用账号"""

    def reset_password(user_id: int, new_password: str) -> bool
        """管理员重置密码"""

    def change_password(user_id: int, old_password: str, new_password: str) -> dict
        """用户自行修改密码"""

    # ---------- 审计 ----------
    def get_login_logs(user_id=None, limit=50) -> list
        """获取登录日志"""

    def get_login_stats(days=7) -> dict
        """登录统计（总登录数/成功失败比/活跃用户）"""
```

### 4.3 app.py 入口改造

```python
# 当前：直接进入主界面
# 改造后：

if not st.session_state.get("auth_user"):
    # 未登录 → 显示登录/注册页面
    render_login_or_register()
else:
    user = st.session_state["auth_user"]

    if user["status"] == "pending":
        # 待审核 → 提示等待
        render_pending_notice()
    elif user["status"] == "disabled":
        # 已禁用 → 提示联系管理员
        render_disabled_notice()
    else:
        # 正常 → 显示功能导航
        render_sidebar(user)  # 根据 role 过滤可见页面
        render_main_content()
```

### 4.4 登录页（login.py）

**布局**：

```
┌─────────────────────────────────────────┐
│           Ksher AgentAI                 │
│        智能工作台 · 用户登录              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  账号                            │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │  密码                            │    │
│  └─────────────────────────────────┘    │
│                                         │
│  [          登  录          ]           │
│                                         │
│  还没有账号？  [立即注册]                │
└─────────────────────────────────────────┘
```

**功能**：
- 账号密码验证
- 登录失败3次后增加验证码（防暴力破解）
- 「记住我」勾选 → Cookie保存7天登录态
- 底部显示系统版本信息

### 4.5 注册页（register.py）

**布局**：

```
┌─────────────────────────────────────────┐
│              用户注册                     │
│                                         │
│  登录账号 *    [______________]         │
│  登录密码 *    [______________]         │
│  确认密码 *    [______________]         │
│  显示昵称      [______________]         │
│  所属渠道商    [______________]         │
│  渠道商编码    [______________]         │
│  联系电话      [______________]         │
│  联系邮箱      [______________]         │
│                                         │
│  [          提  交  注  册    ]         │
│                                         │
│  已有账号？  [返回登录]                  │
└─────────────────────────────────────────┘
```

**表单校验**：
| 字段 | 校验规则 |
|------|---------|
| 账号 | 3-20位，字母开头，字母数字下划线 |
| 密码 | 最少8位，必须包含字母+数字 |
| 确认密码 | 与密码一致 |
| 渠道商编码 | 可选，如填写则格式 KSH-XXX |

**注册后流程**：
```
提交注册 → 前端提示"注册成功，请等待管理员审核"
         → 数据库 status=pending
         → 管理员下次登录时侧边栏显示「待审核(X)」红点
```

### 4.6 管理员后台（admin/user_mgmt.py）

**入口**：侧边栏底部「系统管理」（仅 admin 角色可见）

**Tab 布局**：

```
┌──────────────────────────────────────────────┐
│ 系统管理                                       │
├──────────────────────────────────────────────┤
│ [待审核]  [账号列表]  [新增账号]  [登录日志]      │
├──────────────────────────────────────────────┤
│                                              │
│ Tab1: 待审核列表                              │
│ ┌────────┬────────┬─────────┬────────┐       │
│ │ 账号   │ 昵称   │ 渠道商  │ 操作   │       │
│ ├────────┼────────┼─────────┼────────┤       │
│ │ user01 │ 小王   │ ABC贸易 │ 通过 ✓ │       │
│ │ user02 │ 小李   │ XYZ科技 │ 拒绝 ✗ │       │
│ └────────┴────────┴─────────┴────────┘       │
│                                              │
│ Tab2: 账号列表（搜索/筛选/分页）                │
│ Tab3: 新增账号（后台配号，直接 active）         │
│ Tab4: 登录日志（按时间倒序）                    │
└──────────────────────────────────────────────┘
```

---

## 5. 安全设计

### 5.1 密码安全

| 措施 | 实现 |
|------|------|
| 存储方式 | bcrypt 哈希（salt 自动嵌入） |
| 最低强度 | 8位，至少1字母+1数字 |
| 传输安全 | 依赖 HTTPS（部署层面） |
| 重置密码 | 管理员重置后，用户首次登录强制修改 |

### 5.2 登录安全

| 措施 | 实现 |
|------|------|
| 失败锁定 | 连续5次失败锁定15分钟 |
| 验证码 | 失败3次后启用图形验证码 |
| Session超时 | 30分钟无操作自动失效 |
| 登录日志 | 记录IP、UA、时间、成败 |

### 5.3 默认管理员

首次启动时自动创建默认管理员账号：
- 账号：`admin`
- 密码：随机生成12位字符串，写入 `data/admin_init_password.txt`
- 首次登录强制修改密码
- 密码修改前，每次启动都打印提醒日志

---

## 6. 与现有系统的集成点

### 6.1 数据隔离

当前所有数据（feedback.json、mock_dashboard.json、作战包缓存等）为全局共享。

账号体系引入后，**第一阶段不做数据隔离**（所有登录用户共享同一套数据），**第二阶段可按 channel_code 隔离**。

### 6.2 配置变更

```python
# config.py 新增
AUTH_DB_PATH = os.path.join(DATA_DIR, "auth.db")      # 认证数据库
AUTH_COOKIE_KEY = os.getenv("AUTH_COOKIE_KEY", "ksher_auth_session_2026")  # Cookie签名密钥
AUTH_SESSION_TTL = 60 * 30  # Session 30分钟
AUTH_COOKIE_TTL = 60 * 60 * 24 * 7  # Cookie 7天
```

### 6.3 requirements.txt 新增

```
bcrypt>=4.0.0    # 密码哈希
```

---

## 7. 开发计划

| 阶段 | 内容 | 预估工时 |
|------|------|---------|
| **Day 1 上午** | 数据库初始化 + auth_service.py 核心CRUD | 4h |
| **Day 1 下午** | 登录页 + 注册页 UI + 表单校验 | 4h |
| **Day 2 上午** | app.py 入口改造 + auth_guard + Session管理 | 4h |
| **Day 2 下午** | 管理员后台（4个Tab）+ 默认admin初始化 | 4h |
| **Day 3 上午** | 安全加固（失败锁定/验证码/日志审计） | 3h |
| **Day 3 下午** | 联调测试 + Bug修复 + 文档更新 | 3h |

**总计：约 3 天 / 22 小时**

---

## 8. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| Streamlit无原生路由，登录态通过session_state管理，页面刷新丢失 | 高 | 引入Cookie持久化，刷新后自动恢复登录态 |
| 多人共用admin账号，操作不可追溯 | 中 | 强制首次登录改密码，鼓励每人独立账号 |
| SQLite并发写入性能瓶颈（>100并发） | 低 | 当前场景为内部工具，并发低；未来可迁移至PostgreSQL |
| 密码明文传输（Streamlit不支持前端加密） | 中 | 依赖HTTPS部署，生产环境必须启用SSL |

---

## 9. 评审要点

请评审者确认以下事项：

1. [ ] **角色设计**：`admin / channel / user` 三角色是否满足需求？channel 和 user 是否需要区分？
2. [ ] **页面权限**：财务经理/行政助手是否对渠道商隐藏？其他页面的可见性是否正确？
3. [ ] **注册字段**：渠道商编码格式 `KSH-XXX` 是否合适？还需要哪些字段？
4. [ ] **密码策略**：8位字母+数字是否够用？是否需要大小写+特殊字符？
5. [ ] **数据隔离**：第一阶段不隔离数据是否可接受？第二阶段隔离的优先级？
6. [ ] **部署方式**：是否计划部署到公网？公网必须HTTPS，内网可暂用HTTP。
7. [ ] **开发排期**：3天是否可接受？是否需要压缩或拆分阶段？

---

## 附录 A：待决策问题清单

| # | 问题 | 当前假设 | 需要确认 |
|---|------|---------|---------|
| 1 | 首次启动的默认admin密码 | 随机生成12位，写入文件 | 是否需要短信/邮件通知？ |
| 2 | 待审核通知机制 | 管理员登录后侧边栏红点提示 | 是否需要邮件/短信通知管理员？ |
| 3 | 密码找回功能 | 第一阶段不支持，由管理员重置 | 是否需要自助找回（邮箱验证码）？ |
| 4 | 账号有效期 | 无有效期，长期有效 | 是否需要定期强制修改密码（如90天）？ |
| 5 | 单点登录限制 | 不限制，可多设备同时登录 | 是否需要限制同一账号同时在线数？ |
| 6 | 渠道商自管理 | 渠道商不能管理自己的子账号 | 是否需要 channel 角色也能创建子账号？ |

---

*文档版本：v1.0*
*创建日期：2026-04-20*
*作者：AI 设计助手*
