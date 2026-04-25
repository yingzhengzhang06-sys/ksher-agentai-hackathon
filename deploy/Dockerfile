# Ksher AgentAI 数字员工 — 生产环境 Docker 镜像
# 多阶段构建：Python 基础镜像 + Chrome for Playwright

# 阶段 1: Python 基础镜像
FROM python:3.14-slim AS python-base

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js（用于前端构建，如有需要）
RUN wget -qO- https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 安装 Chrome（用于 Playwright/html2image）
RUN wget -q -O - https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm ./google-chrome-stable_current_amd64.deb

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 阶段 2: 最终运行镜像
FROM python:3.14-slim AS runtime

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libxrandr2 \
    libxscrn saver1 \
    libxtst6 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libpango-1.0-0 \
    libwayland-cursor0 \
    libwayland-egl1 \
    libxkbcommon0 \
    libxcomposite1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 安装 Chrome（用于 html2image 渲染）
RUN wget -q -O - https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm ./google-chrome-stable_current_amd64.deb

# 从 Python 基础镜像复制已安装的包和代码
COPY --from=python-base /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=python-base /app /app

# 创建非 root 用户
RUN useradd -m -s /bin/bash -u 1001 ksher_user
USER ksher_user

# 设置工作目录
WORKDIR /app

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 启动命令（使用 supervisord）
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
