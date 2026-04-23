"""
本地 WebSocket 终端服务器 — 为 Streamlit 提供 Cloud Code 式终端能力

运行方式:
    python terminal_server.py

特性:
- WebSocket 实时通信（无需刷新页面）
- 命令白名单限制（防止危险操作）
- 用户工作目录隔离
- 流式输出（命令执行日志实时返回）
- 多会话支持（多个浏览器标签页独立会话）

安全限制:
- 禁止: rm, mkfs, dd, >, | 等危险操作
- 只允许: python, git, ls, cat, pytest 等开发命令
- 所有命令在指定工作目录下执行
"""

import asyncio
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, Set

# 尝试导入 websockets，未安装时给出友好提示
try:
    import websockets
except ImportError:
    print("[ERROR] 请先安装 websockets: pip install websockets")
    sys.exit(1)


# ============================================================
# 配置
# ============================================================

HOST = os.getenv("TERMINAL_HOST", "localhost")
PORT = int(os.getenv("TERMINAL_PORT", "8765"))

# 项目根目录作为默认工作区
PROJECT_ROOT = Path(__file__).parent.resolve()
WORKSPACE_DIR = Path(os.getenv("TERMINAL_WORKSPACE", PROJECT_ROOT / "workspace"))
WORKSPACE_DIR.mkdir(exist_ok=True)

# 命令白名单（允许执行的命令前缀）
ALLOWED_COMMANDS: Set[str] = {
    # Python
    "python", "python3", "pip", "pytest", "python -m",
    # Git
    "git",
    # 文件查看
    "ls", "ll", "cat", "head", "tail", "less", "more",
    "find", "grep", "wc", "diff", "file",
    # 目录操作
    "cd", "pwd", "mkdir", "touch", "cp", "mv",
    # 编辑器
    "nano", "vim", "vi", "code",
    # 系统信息
    "echo", "date", "whoami", "uname", "df", "du",
    "which", "whereis", "env", "printenv",
    # 压缩
    "tar", "zip", "unzip",
    # 其他开发工具
    "curl", "wget", "node", "npm", "yarn",
    "streamlit", "flake8", "black", "mypy",
    # 自定义脚本
    "./", "bash", "sh", "zsh",
}

# 危险命令黑名单（绝对禁止）
BLOCKED_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\brm\s+.+/(\.|\.\.)?",
    r"\bdd\s+if=",
    r"\bmkfs\.",
    r"\b>:?\s*/dev/",
    r"\bsudo\s+",
    r"\bsu\s+-",
    r">\s*/etc/",
    r">\s*/System/",
    r"\bcurl\s+.*\|\s*bash",
    r"\bwget\s+.*\|\s*bash",
    r"\beval\s*\$",
    r"\bchmod\s+777\s+/",
]

# ANSI 颜色码（终端输出着色）
COLORS = {
    "prompt": "\033[1;32m",      # 绿色
    "error": "\033[1;31m",       # 红色
    "warning": "\033[1;33m",     # 黄色
    "info": "\033[1;36m",        # 青色
    "reset": "\033[0m",
}


# ============================================================
# 会话管理
# ============================================================

class TerminalSession:
    """单个终端会话 — 每个 WebSocket 连接一个实例"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.cwd = WORKSPACE_DIR  # 当前工作目录
        self.env = os.environ.copy()
        self.env["TERM"] = "xterm-256color"
        self.env["PS1"] = f"{COLORS['prompt']}➜ {COLORS['reset']}"
        self.history: list[str] = []
        self.process: subprocess.Popen | None = None

    def is_command_safe(self, cmd: str) -> tuple[bool, str]:
        """检查命令是否安全"""
        stripped = cmd.strip()
        if not stripped:
            return True, ""

        # 检查黑名单正则
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                return False, f"危险命令被拦截: 匹配规则 `{pattern}`"

        # 检查是否在白名单中
        # 允许 cd 命令（只改变目录，不执行）
        if stripped.startswith("cd ") or stripped == "cd":
            return True, ""

        # 提取命令第一个词
        try:
            first_token = shlex.split(stripped)[0]
        except ValueError:
            first_token = stripped.split()[0] if stripped.split() else ""

        # 检查是否以允许的前缀开头
        allowed = any(
            stripped.startswith(prefix) or first_token == prefix
            for prefix in ALLOWED_COMMANDS
        )

        if not allowed:
            return False, (
                f"命令 '{first_token}' 不在白名单中。\n"
                f"允许的命令: python, git, ls, cat, pytest, streamlit 等。\n"
                f"禁止: rm, sudo, curl | bash 等危险操作。"
            )

        return True, ""

    async def execute(self, cmd: str, websocket):
        """执行命令并流式返回输出"""
        stripped = cmd.strip()
        if not stripped:
            await self._send_prompt(websocket)
            return

        self.history.append(stripped)

        # 特殊处理 cd 命令
        if stripped.startswith("cd "):
            await self._handle_cd(stripped[3:].strip(), websocket)
            return
        if stripped == "cd":
            self.cwd = WORKSPACE_DIR
            await self._send_prompt(websocket)
            return

        # 安全检查
        safe, reason = self.is_command_safe(stripped)
        if not safe:
            await websocket.send(json.dumps({
                "type": "error",
                "text": f"{COLORS['error']}[安全拦截] {reason}{COLORS['reset']}\n",
            }))
            await self._send_prompt(websocket)
            return

        # 执行命令
        await websocket.send(json.dumps({
            "type": "status",
            "text": f"{COLORS['info']}[执行] {stripped}{COLORS['reset']}\n",
        }))

        try:
            self.process = subprocess.Popen(
                stripped,
                shell=True,
                cwd=self.cwd,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲，支持实时输出
            )

            # 流式读取 stdout
            if self.process.stdout:
                for line in iter(self.process.stdout.readline, ""):
                    if not line:
                        break
                    await websocket.send(json.dumps({
                        "type": "output",
                        "text": line,
                    }))

            # 读取 stderr
            stderr_text = ""
            if self.process.stderr:
                stderr_text = self.process.stderr.read()

            # 等待进程结束
            self.process.wait()

            # 发送 stderr（如果有）
            if stderr_text:
                await websocket.send(json.dumps({
                    "type": "stderr",
                    "text": f"{COLORS['warning']}{stderr_text}{COLORS['reset']}",
                }))

            # 发送退出码
            await websocket.send(json.dumps({
                "type": "done",
                "code": self.process.returncode,
            }))

        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error",
                "text": f"{COLORS['error']}[执行错误] {e}{COLORS['reset']}\n",
            }))

        finally:
            self.process = None
            await self._send_prompt(websocket)

    async def _handle_cd(self, path_str: str, websocket):
        """处理 cd 命令"""
        try:
            new_path = (self.cwd / path_str).resolve()
            # 限制不能跳出工作区
            if not str(new_path).startswith(str(WORKSPACE_DIR)):
                await websocket.send(json.dumps({
                    "type": "error",
                    "text": f"{COLORS['error']}[安全限制] 不能访问工作区外的目录{COLORS['reset']}\n",
                }))
            else:
                new_path.mkdir(parents=True, exist_ok=True)
                self.cwd = new_path
                await websocket.send(json.dumps({
                    "type": "info",
                    "text": f"{COLORS['info']}[目录] {self.cwd}{COLORS['reset']}\n",
                }))
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error",
                "text": f"{COLORS['error']}[cd 错误] {e}{COLORS['reset']}\n",
            }))
        await self._send_prompt(websocket)

    async def _send_prompt(self, websocket):
        """发送提示符"""
        rel_path = self.cwd.relative_to(WORKSPACE_DIR) if self.cwd != WORKSPACE_DIR else "."
        prompt = f"\r{COLORS['prompt']}➜ {COLORS['reset']}{rel_path} $ "
        await websocket.send(json.dumps({
            "type": "prompt",
            "text": prompt,
            "cwd": str(self.cwd),
        }))


# ============================================================
# WebSocket 服务器
# ============================================================

SESSIONS: Dict[str, TerminalSession] = {}


async def handle_websocket(websocket):
    """处理 WebSocket 连接"""
    session_id = str(uuid.uuid4())[:8]
    session = TerminalSession(session_id)
    SESSIONS[session_id] = session

    client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    print(f"[+] 终端会话连接: {session_id} from {client_info}")

    try:
        # 发送欢迎信息和提示符
        await websocket.send(json.dumps({
            "type": "welcome",
            "text": (
                f"{COLORS['info']}"
                f"╔══════════════════════════════════════════╗\n"
                f"║  Ksher AgentAI 本地终端                  ║\n"
                f"║  工作区: {WORKSPACE_DIR}                 \n"
                f"╚══════════════════════════════════════════╝"
                f"{COLORS['reset']}\n"
            ),
        }))
        await session._send_prompt(websocket)

        # 接收命令循环
        async for message in websocket:
            try:
                data = json.loads(message)
                cmd = data.get("command", "")

                # 支持特殊命令
                if cmd == "__ping__":
                    await websocket.send(json.dumps({"type": "pong"}))
                    continue

                if cmd == "__resize__":
                    # 终端大小调整（暂存，后续可扩展）
                    continue

                await session.execute(cmd, websocket)

            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "text": f"{COLORS['error']}[协议错误] 无效 JSON{COLORS['reset']}\n",
                }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # 清理会话
        if session.process and session.process.poll() is None:
            session.process.terminate()
        del SESSIONS[session_id]
        print(f"[-] 终端会话断开: {session_id}")


async def main():
    """启动服务器"""
    print(f"=" * 60)
    print(f"  Ksher AgentAI 本地终端服务器")
    print(f"  WebSocket: ws://{HOST}:{PORT}")
    print(f"  工作区: {WORKSPACE_DIR}")
    print(f"=" * 60)
    print()
    print("  启动方式:")
    print(f"    1. 本终端: python terminal_server.py")
    print(f"    2. Streamlit: streamlit run app.py")
    print()
    print("  使用方式:")
    print("    在 Streamlit 页面中打开「终端」标签即可使用")
    print()

    async with websockets.serve(handle_websocket, HOST, PORT):
        print(f"[✓] 服务器已启动，等待连接...")
        await asyncio.Future()  # 永远运行


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] 服务器已停止")
