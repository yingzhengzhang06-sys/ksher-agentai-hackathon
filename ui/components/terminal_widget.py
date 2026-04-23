"""
终端小部件 — 在 Streamlit 页面中嵌入交互式终端

使用 xterm.js 通过 WebSocket 连接到本地 terminal_server.py
"""
import streamlit as st

TERMINAL_WIDGET_HTML = """
<style>
.terminal-container {
    background: #1e1e1e;
    border-radius: 8px;
    padding: 4px;
    height: 500px;
    overflow: hidden;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
}
.terminal-header {
    background: #2d2d2d;
    padding: 6px 12px;
    border-radius: 6px 6px 0 0;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #888;
}
.terminal-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.terminal-dot.red { background: #ff5f56; }
.terminal-dot.yellow { background: #ffbd2e; }
.terminal-dot.green { background: #27c93f; }
#terminal-{terminal_id} {
    height: calc(500px - 30px);
    padding: 8px;
}
.terminal-status {
    font-size: 11px;
    color: #666;
    padding: 4px 12px;
    background: #1e1e1e;
    border-top: 1px solid #333;
}
.terminal-status.connected { color: #27c93f; }
.terminal-status.disconnected { color: #ff5f56; }
</style>

<div class="terminal-container">
    <div class="terminal-header">
        <span class="terminal-dot red"></span>
        <span class="terminal-dot yellow"></span>
        <span class="terminal-dot green"></span>
        <span style="margin-left:8px;">本地终端 — ws://localhost:8765</span>
    </div>
    <div id="terminal-{terminal_id}"></div>
    <div id="terminal-status-{terminal_id}" class="terminal-status disconnected">
        ● 连接中...
    </div>
</div>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
<script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>

<script>
(function() {{
    const terminalId = "{terminal_id}";
    const wsUrl = "ws://localhost:8765";
    let ws = null;
    let term = null;
    let fitAddon = null;
    let currentInput = "";
    let isConnected = false;

    function initTerminal() {{
        const container = document.getElementById("terminal-" + terminalId);
        if (!container) {{
            console.error("Terminal container not found");
            return;
        }}

        // 清理已有内容
        container.innerHTML = "";

        term = new Terminal({{
            fontSize: 13,
            fontFamily: "'Menlo', 'Monaco', 'Courier New', monospace",
            theme: {{
                background: '#1e1e1e',
                foreground: '#d4d4d4',
                cursor: '#d4d4d4',
                selectionBackground: '#264f78',
                black: '#1e1e1e',
                red: '#f48771',
                green: '#89d185',
                yellow: '#dcdcaa',
                blue: '#569cd6',
                magenta: '#c586c0',
                cyan: '#4ec9b0',
                white: '#d4d4d4',
            }},
            cursorBlink: true,
            scrollback: 5000,
        }});

        fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(container);
        fitAddon.fit();

        // 处理键盘输入
        term.onData(function(data) {{
            if (!isConnected || !ws) {{
                term.write("\\r\\n[未连接] 请先启动终端服务器: python terminal_server.py\\r\\n");
                return;
            }}

            const code = data.charCodeAt(0);

            // Enter (CR 或 LF)
            if (code === 13 || code === 10) {{
                ws.send(JSON.stringify({{command: currentInput}}));
                currentInput = "";
            }}
            // Backspace
            else if (code === 127) {{
                if (currentInput.length > 0) {{
                    currentInput = currentInput.slice(0, -1);
                    term.write("\\b \\b");
                }}
            }}
            // Ctrl+C
            else if (code === 3) {{
                ws.send(JSON.stringify({{command: "__ctrl_c__"}}));
                currentInput = "";
                term.write("^C\\r\\n");
            }}
            // Ctrl+L
            else if (code === 12) {{
                term.clear();
            }}
            // 可打印字符
            else if (code >= 32 && code < 127) {{
                currentInput += data;
                term.write(data);
            }}
        }});

        connectWebSocket();
    }}

    function connectWebSocket() {{
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {{
            isConnected = true;
            updateStatus("已连接", true);
        }};

        ws.onmessage = function(event) {{
            try {{
                const msg = JSON.parse(event.data);
                if (msg.text) {{
                    term.write(msg.text);
                }}
                if (msg.type === "prompt") {{
                    currentInput = "";
                }}
            }} catch (e) {{
                term.write(event.data);
            }}
        }};

        ws.onclose = function() {{
            isConnected = false;
            updateStatus("已断开", false);
            // 3秒后重连
            setTimeout(connectWebSocket, 3000);
        }};

        ws.onerror = function(err) {{
            isConnected = false;
            updateStatus("连接错误", false);
        }};
    }}

    function updateStatus(text, connected) {{
        const el = document.getElementById("terminal-status-" + terminalId);
        if (el) {{
            el.textContent = (connected ? "● " : "○ ") + text;
            el.className = "terminal-status " + (connected ? "connected" : "disconnected");
        }}
    }}

    // 延迟初始化，确保 DOM 已就绪
    setTimeout(initTerminal, 500);

    // 窗口大小改变时自适应
    window.addEventListener("resize", function() {{
        if (fitAddon) fitAddon.fit();
    }});
}})();
</script>
"""


def render_terminal_widget():
    """在 Streamlit 页面中渲染终端小部件"""
    import uuid as _uuid

    terminal_id = _uuid.uuid4().hex[:8]
    html = TERMINAL_WIDGET_HTML.format(terminal_id=terminal_id)
    st.html(html)

    # 显示帮助信息
    with st.expander("使用说明", expanded=False):
        st.markdown("""
        **终端功能说明：**

        1. **先启动终端服务器**（在另一个终端窗口执行）：
           ```bash
           python terminal_server.py
           ```

        2. **支持的命令**（白名单）：
           - `python`, `python3`, `pip`, `pytest`
           - `git`（clone, status, log, diff 等）
           - `ls`, `cat`, `head`, `tail`, `find`, `grep`
           - `cd`, `pwd`, `mkdir`, `cp`, `mv`
           - `streamlit`, `flake8`, `black`

        3. **安全限制**：
           - 禁止 `rm -rf /`, `sudo`, `curl | bash` 等危险操作
           - 命令在工作目录下执行，不能访问工作区外文件
           - 所有操作在本地完成，无网络请求

        4. **快捷键**：
           - `Ctrl+C` — 中断当前命令
           - `Ctrl+L` — 清屏
        """)
