# =======================================================
# MediaCrawler 生产容器镜像构建文件 (Python 3.11 + Node.js 20)
# =======================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

WORKDIR /app

# 1. 安装基础工具与 Node.js 20 (运行签名服务)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    build-essential \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 uv 包管理器（极速安装与管理 Python 虚拟环境）
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 3. 预先拷贝依赖文件以利用 Docker 缓存层
COPY pyproject.toml uv.lock ./

# 4. 同步安装 Python 依赖
RUN uv sync --frozen --no-dev

# 5. 拷贝项目源码
COPY . .

# 6. 设置执行权限
RUN chmod +x docker-entrypoint.sh 2>/dev/null || true

# 暴露服务端口:
# 8080: MediaCrawler FastAPI Web / API 服务
# 8999: Node.js 签名微服务
EXPOSE 8080 8999

# 启动入口脚本
CMD ["/bin/bash", "docker-entrypoint.sh"]

