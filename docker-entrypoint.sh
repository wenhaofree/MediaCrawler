#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🚀 正在启动 MediaCrawler 生产容器服务..."
echo "=========================================================="

# 1. 确保环境变量文件存在
if [ ! -f .env ] && [ -f .env.example ]; then
    echo "⚠️ 未发现 .env 文件，自动从 .env.example 复制默认配置..."
    cp .env.example .env
fi

# 2. 如果开启了自动初始化数据库 (由环境变量 AUTO_INIT_DB 控制，默认开启)
if [ "${AUTO_INIT_DB:-true}" = "true" ]; then
    DB_TYPE="${SAVE_DATA_OPTION:-postgres}"
    echo "📦 正在初始化 ${DB_TYPE} 数据库表结构 (自动建表/迁移)..."
    uv run python -c "
import asyncio
from database.db_session import create_tables
import config
asyncio.run(create_tables('${DB_TYPE}'))
print('✅ 数据库表结构初始化/检查完成')
" || echo "⚠️ 数据库初始化警告（若数据库尚未启动就绪可稍后重试）"
fi

# 3. 启动后台 Node.js 签名微服务 (端口 8999)
echo "🔑 启动后台 Node.js 签名微服务 (http://127.0.0.1:8999)..."
node services/sign_srv/server.js &
SIGN_SRV_PID=$!

# 等待签名微服务就绪
sleep 1

# 4. 启动 FastAPI API 核心服务 (端口 8080)
echo "🌐 启动 MediaCrawler Web / API 核心服务 (0.0.0.0:8080)..."
exec uv run uvicorn api.main:app --host 0.0.0.0 --port 8080

