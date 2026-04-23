#!/usr/bin/env python3
"""
一键启动脚本 — 同时启动 Streamlit + 终端服务器

用法:
    python start_with_terminal.py

功能:
- 启动 terminal_server.py（WebSocket 终端服务）
- 启动 Streamlit 应用
- 自动检测依赖是否安装
- 优雅关闭（Ctrl+C 同时停止两个服务）
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def check_dependency():
    """检查 websockets 是否已安装"""
    try:
        import websockets
        return True
    except ImportError:
        return False


def main():
    project_root = Path(__file__).parent.resolve()
    os.chdir(project_root)

    print("=" * 60)
    print("  Ksher AgentAI 智能工作台 — 带终端模式")
    print("=" * 60)
    print()

    # 检查依赖
    if not check_dependency():
        print("[✗] 缺少 websockets 依赖")
        print("    请运行: pip install websockets")
        print()
        sys.exit(1)

    print("[✓] 依赖检查通过")
    print()

    # 启动终端服务器
    print("[→] 启动终端服务器...")
    terminal_proc = subprocess.Popen(
        [sys.executable, "terminal_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # 等待终端服务器启动
    time.sleep(1.5)
    if terminal_proc.poll() is not None:
        print("[✗] 终端服务器启动失败")
        out, _ = terminal_proc.communicate()
        if out:
            print(out)
        sys.exit(1)

    print("[✓] 终端服务器已启动 (ws://localhost:8765)")
    print()

    # 启动 Streamlit
    print("[→] 启动 Streamlit...")
    print()

    streamlit_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    processes = [terminal_proc, streamlit_proc]

    def cleanup(signum, frame):
        """优雅关闭所有进程"""
        print("\n[!] 正在停止服务...")
        for p in processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
        print("[✓] 所有服务已停止")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # 合并输出两个服务的日志
    try:
        while True:
            for p in processes:
                if p.poll() is not None:
                    # 某个进程退出
                    cleanup(None, None)

            # 非阻塞读取输出
            import select
            for p in processes:
                if p.stdout:
                    readable, _, _ = select.select([p.stdout], [], [], 0.1)
                    if readable:
                        line = p.stdout.readline()
                        if line:
                            print(line, end="")

            time.sleep(0.05)

    except KeyboardInterrupt:
        cleanup(None, None)


if __name__ == "__main__":
    main()
