# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/database/db_session.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from .models import Base
import config
from config.db_config import mysql_db_config, sqlite_db_config, postgres_db_config

# Keep a cache of engines
_engines = {}


async def create_database_if_not_exists(db_type: str):
    if db_type == "mysql" or db_type == "db":
        # Connect to the server without a database
        server_url = f"mysql+asyncmy://{mysql_db_config['user']}:{mysql_db_config['password']}@{mysql_db_config['host']}:{mysql_db_config['port']}"
        engine = create_async_engine(server_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {mysql_db_config['db_name']}"))
        await engine.dispose()
    elif db_type == "postgres":
        # Connect to the default 'postgres' database
        server_url = f"postgresql+asyncpg://{postgres_db_config['user']}:{postgres_db_config['password']}@{postgres_db_config['host']}:{postgres_db_config['port']}/postgres"
        print(f"[init_db] Connecting to Postgres: host={postgres_db_config['host']}, port={postgres_db_config['port']}, user={postgres_db_config['user']}, dbname=postgres")
        # Isolation level AUTOCOMMIT is required for CREATE DATABASE
        engine = create_async_engine(server_url, echo=False, isolation_level="AUTOCOMMIT")
        async with engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{postgres_db_config['db_name']}'"))
            if not result.scalar():
                await conn.execute(text(f"CREATE DATABASE {postgres_db_config['db_name']}"))
        await engine.dispose()


def get_async_engine(db_type: str = None):
    if db_type is None:
        db_type = config.SAVE_DATA_OPTION

    if db_type in _engines:
        return _engines[db_type]

    if db_type in ["json", "jsonl", "csv"]:
        return None

    if db_type == "sqlite":
        db_url = f"sqlite+aiosqlite:///{sqlite_db_config['db_path']}"
    elif db_type == "mysql" or db_type == "db":
        db_url = f"mysql+asyncmy://{mysql_db_config['user']}:{mysql_db_config['password']}@{mysql_db_config['host']}:{mysql_db_config['port']}/{mysql_db_config['db_name']}"
    elif db_type == "postgres":
        db_url = f"postgresql+asyncpg://{postgres_db_config['user']}:{postgres_db_config['password']}@{postgres_db_config['host']}:{postgres_db_config['port']}/{postgres_db_config['db_name']}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    engine = create_async_engine(db_url, echo=False)
    _engines[db_type] = engine
    return engine


def _migrate_missing_columns(sync_conn):
    """
    Automatically migrate missing columns from ORM models to existing database tables.
    This ensures backward compatibility when new columns are added to models.
    """
    from sqlalchemy import inspect
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue
        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name not in existing_cols:
                col_type = column.type.compile(sync_conn.dialect)
                default_clause = ""
                if column.server_default is not None:
                    default_clause = f" DEFAULT {column.server_default.arg}"
                elif column.default is not None and column.default.is_scalar:
                    val = column.default.arg
                    if isinstance(val, str):
                        default_clause = f" DEFAULT '{val}'"
                    elif val is not None:
                        default_clause = f" DEFAULT {val}"
                elif not column.nullable:
                    default_clause = " DEFAULT ''"

                null_clause = " NOT NULL" if (not column.nullable and default_clause) else ""
                sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {col_type}{default_clause}{null_clause}'
                try:
                    sync_conn.execute(text(sql))
                except Exception:
                    pass

                if column.index:
                    idx_sql = f'CREATE INDEX IF NOT EXISTS "ix_{table_name}_{column.name}" ON "{table_name}" ("{column.name}")'
                    try:
                        sync_conn.execute(text(idx_sql))
                    except Exception:
                        pass


def _rename_legacy_tables(sync_conn):
    """
    Rename legacy table names to standardized platform table names (e.g. dy_creator -> douyin_creator).
    """
    from sqlalchemy import inspect
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    legacy_renames = [
        ("dy_creator", "douyin_creator"),
    ]
    for old_name, new_name in legacy_renames:
        if old_name in existing_tables and new_name not in existing_tables:
            try:
                sync_conn.execute(text(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"'))
            except Exception:
                try:
                    sync_conn.execute(text(f"ALTER TABLE {old_name} RENAME TO {new_name}"))
                except Exception:
                    pass


def _migrate_gzh_uniqueness(sync_conn):
    """
    Deduplicate gzh_article / gzh_account rows, then ensure unique indexes:
    - gzh_account.account_id
    - gzh_article.review_id
    - gzh_article.original_id (partial, non-empty only)
    """
    from sqlalchemy import inspect

    inspector = inspect(sync_conn)
    tables = set(inspector.get_table_names())
    dialect = sync_conn.dialect.name

    if "gzh_article" in tables:
        # Normalize empty original_id to NULL so partial unique index works.
        try:
            sync_conn.execute(
                text(
                    "UPDATE gzh_article SET original_id = NULL "
                    "WHERE original_id IS NOT NULL AND BTRIM(CAST(original_id AS TEXT)) = ''"
                )
            )
        except Exception:
            pass

        # Merge duplicate logical articles (same account + title), keep best row.
        try:
            dup_rows = sync_conn.execute(
                text(
                    """
                    SELECT account_id, title
                    FROM gzh_article
                    WHERE account_id IS NOT NULL AND title IS NOT NULL AND title <> ''
                    GROUP BY account_id, title
                    HAVING COUNT(*) > 1
                    """
                )
            ).fetchall()
            for account_id, title in dup_rows:
                rows = sync_conn.execute(
                    text(
                        """
                        SELECT id, review_id, original_id, read_count, like_count,
                               article_url, cover_url, summary, account_name, published_at
                        FROM gzh_article
                        WHERE account_id = :account_id AND title = :title
                        ORDER BY id ASC
                        """
                    ),
                    {"account_id": account_id, "title": title},
                ).fetchall()
                if len(rows) < 2:
                    continue

                def _score(r):
                    return (
                        1 if r.read_count is not None else 0,
                        1 if (r.original_id or "") else 0,
                        1 if "_WR" in (r.review_id or "") else 0,
                        len(r.review_id or ""),
                        r.id or 0,
                    )

                keep = max(rows, key=_score)
                keep_id = keep.id
                best_review = keep.review_id
                best_original = keep.original_id
                best_read = keep.read_count
                best_like = keep.like_count
                best_url = keep.article_url or ""
                best_cover = keep.cover_url or ""
                best_summary = keep.summary or ""
                best_name = keep.account_name or ""
                best_published = keep.published_at
                for r in rows:
                    if r.id == keep_id:
                        continue
                    if (r.original_id or "") and not (best_original or ""):
                        best_original = r.original_id
                    if r.read_count is not None and best_read is None:
                        best_read = r.read_count
                    if r.like_count is not None and best_like is None:
                        best_like = r.like_count
                    if (r.article_url or "") and not best_url:
                        best_url = r.article_url
                    if (r.cover_url or "") and not best_cover:
                        best_cover = r.cover_url
                    if (r.summary or "") and not best_summary:
                        best_summary = r.summary
                    if (r.account_name or "") and not best_name:
                        best_name = r.account_name
                    if r.published_at is not None and best_published is None:
                        best_published = r.published_at
                    if "_WR" in (r.review_id or "") and "_WR" not in (best_review or ""):
                        best_review = r.review_id
                    elif len(r.review_id or "") > len(best_review or "") and "_WR" in (r.review_id or ""):
                        best_review = r.review_id
                    sync_conn.execute(
                        text("DELETE FROM gzh_article WHERE id = :id"),
                        {"id": r.id},
                    )
                sync_conn.execute(
                    text(
                        """
                        UPDATE gzh_article SET
                          review_id = :review_id,
                          original_id = :original_id,
                          read_count = :read_count,
                          like_count = :like_count,
                          article_url = :article_url,
                          cover_url = :cover_url,
                          summary = :summary,
                          account_name = :account_name,
                          published_at = :published_at
                        WHERE id = :keep_id
                        """
                    ),
                    {
                        "review_id": best_review,
                        "original_id": best_original,
                        "read_count": best_read,
                        "like_count": best_like,
                        "article_url": best_url,
                        "cover_url": best_cover,
                        "summary": best_summary,
                        "account_name": best_name,
                        "published_at": best_published,
                        "keep_id": keep_id,
                    },
                )
        except Exception:
            pass

        # Drop non-unique index then create unique on review_id
        try:
            if dialect == "postgresql":
                sync_conn.execute(text("DROP INDEX IF EXISTS ix_gzh_article_review_id"))
                sync_conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_gzh_article_review_id "
                        "ON gzh_article (review_id)"
                    )
                )
                sync_conn.execute(text("DROP INDEX IF EXISTS ix_gzh_article_original_id"))
                sync_conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_gzh_article_original_id "
                        "ON gzh_article (original_id) "
                        "WHERE original_id IS NOT NULL AND original_id <> ''"
                    )
                )
            else:
                sync_conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_gzh_article_review_id "
                        "ON gzh_article (review_id)"
                    )
                )
                sync_conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_gzh_article_original_id "
                        "ON gzh_article (original_id) "
                        "WHERE original_id IS NOT NULL AND original_id <> ''"
                    )
                )
        except Exception:
            pass

    if "gzh_account" in tables:
        try:
            # Deduplicate account_id keeping lowest id
            sync_conn.execute(
                text(
                    """
                    DELETE FROM gzh_account a
                    WHERE a.id NOT IN (
                        SELECT MIN(id) FROM gzh_account GROUP BY account_id
                    )
                    """
                )
            )
        except Exception:
            # SQLite correlated delete may differ; ignore if unsupported
            pass
        try:
            if dialect == "postgresql":
                sync_conn.execute(text("DROP INDEX IF EXISTS ix_gzh_account_account_id"))
            sync_conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_gzh_account_account_id "
                    "ON gzh_account (account_id)"
                )
            )
        except Exception:
            pass


async def create_tables(db_type: str = None):
    if db_type is None:
        db_type = config.SAVE_DATA_OPTION
    await create_database_if_not_exists(db_type)
    engine = get_async_engine(db_type)
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(_rename_legacy_tables)
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_migrate_missing_columns)
            await conn.run_sync(_migrate_gzh_uniqueness)


@asynccontextmanager
async def get_session() -> AsyncSession:
    engine = get_async_engine(config.SAVE_DATA_OPTION)
    if not engine:
        yield None
        return
    AsyncSessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()
