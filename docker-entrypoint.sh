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

# 持久化调度库目录（SQLITE_DB_PATH 默认指向 /app/data/sqlite_tables.db）
mkdir -p /app/data

# 2. 如果开启了自动初始化数据库 (由环境变量 AUTO_INIT_DB 控制，默认开启)
if [ "${AUTO_INIT_DB:-true}" = "true" ]; then
    DB_TYPE="${SAVE_DATA_OPTION:-postgres}"
    echo "📦 正在初始化 ${DB_TYPE} 数据库表结构 (自动建表/迁移，含快照表)..."
    SAVE_DATA_OPTION="${DB_TYPE}" uv run python - <<'PY'
import asyncio
import os

from sqlalchemy import text

from database.db_session import create_tables, get_async_engine

DB_TYPE = os.environ.get("SAVE_DATA_OPTION", "postgres")


async def main() -> None:
    await create_tables(DB_TYPE)
    engine = get_async_engine(DB_TYPE)
    required = ("douyin_creator_stats", "douyin_aweme_stats", "douyin_creator", "douyin_aweme")
    async with engine.connect() as conn:
        if DB_TYPE == "postgres":
            rows = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            tables = {row[0] for row in rows.fetchall()}
        else:
            rows = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = {row[0] for row in rows.fetchall()}

    print("✅ 数据库表结构初始化/检查完成")
    print(
        "   快照表: douyin_creator_stats="
        + ("OK" if "douyin_creator_stats" in tables else "MISSING")
    )
    print(
        "   快照表: douyin_aweme_stats="
        + ("OK" if "douyin_aweme_stats" in tables else "MISSING")
    )
    missing = [name for name in required if name not in tables]
    if missing:
        raise SystemExit(f"❌ 缺少必要表: {', '.join(missing)}")


asyncio.run(main())
PY
fi

# 3. 启动后台 Node.js 签名微服务 (端口 8999)
echo "🔑 启动后台 Node.js 签名微服务 (http://127.0.0.1:8999)..."
node services/sign_srv/server.js &

# 等待签名微服务就绪
sleep 1

# 4. 启动 FastAPI API 核心服务 (端口 8080)
#    启动时会 ensure_tables + ensure_default_douyin_schedule（若 AUTO_SEED_DY_SCHEDULE=true）
echo "🌐 启动 MediaCrawler Web / API 核心服务 (0.0.0.0:8080)..."
echo "   AUTO_SEED_DY_SCHEDULE=${AUTO_SEED_DY_SCHEDULE:-false}"
echo "   SCHEDULED_CRAWL_PURE_API=${SCHEDULED_CRAWL_PURE_API:-false}"
echo "   DY_SCHEDULE_RUN_TIME=${DY_SCHEDULE_RUN_TIME:-09:00,14:00,22:30}"
exec uv run uvicorn api.main:app --host 0.0.0.0 --port 8080
