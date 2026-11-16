# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select

from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import GzhAccount, GzhAccountStats, GzhArticle
from media_platform.douyin.lifecycle import collected_at_iso, parse_count, resolve_scheduled_slot
from tools import utils
from var import crawler_type_var, should_write_gzh_account_stats

_ACCOUNT_META_KEYS = (
    "_write_stats",
    "_sample_article_count",
    "_total_read_count",
    "_total_like_count",
    "_source_type",
)


def _pop_meta(item: Dict[str, Any]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    for key in _ACCOUNT_META_KEYS:
        if key in item:
            meta[key] = item.pop(key)
    return meta


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    parsed = parse_count(value)
    if parsed is None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return int(parsed)


class GzhDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        item = dict(content_item)
        review_id = (item.get("review_id") or "").strip()
        original_id = (item.get("original_id") or "").strip()
        if not review_id and not original_id:
            return

        item["read_count"] = _to_int(item.get("read_count"))
        item["like_count"] = _to_int(item.get("like_count"))
        item["published_at"] = _to_int(item.get("published_at"))

        async with get_session() as session:
            row = None
            if review_id:
                result = await session.execute(
                    select(GzhArticle).where(GzhArticle.review_id == review_id)
                )
                row = result.scalars().first()
            if row is None and original_id:
                result = await session.execute(
                    select(GzhArticle).where(GzhArticle.original_id == original_id)
                )
                row = result.scalars().first()

            now_ts = utils.get_current_timestamp()
            payload = {
                "review_id": review_id or (row.review_id if row else original_id),
                "original_id": original_id or (row.original_id if row else ""),
                "account_id": item.get("account_id") or (row.account_id if row else ""),
                "title": item.get("title") if item.get("title") is not None else (row.title if row else ""),
                "summary": item.get("summary") if item.get("summary") is not None else (row.summary if row else ""),
                "account_name": item.get("account_name")
                if item.get("account_name") is not None
                else (row.account_name if row else ""),
                "article_url": item.get("article_url")
                if item.get("article_url") is not None
                else (row.article_url if row else ""),
                "cover_url": item.get("cover_url")
                if item.get("cover_url") is not None
                else (row.cover_url if row else ""),
                "published_at": item.get("published_at")
                if item.get("published_at") is not None
                else (row.published_at if row else None),
                "last_modify_ts": now_ts,
            }
            # Only overwrite engagement when provided
            if item.get("read_count") is not None:
                payload["read_count"] = item["read_count"]
            elif row is not None:
                payload["read_count"] = row.read_count
            if item.get("like_count") is not None:
                payload["like_count"] = item["like_count"]
            elif row is not None:
                payload["like_count"] = row.like_count

            if not row:
                payload["add_ts"] = now_ts
                if "read_count" not in payload:
                    payload["read_count"] = None
                if "like_count" not in payload:
                    payload["like_count"] = None
                session.add(GzhArticle(**payload))
            else:
                for key, value in payload.items():
                    setattr(row, key, value)
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        item = dict(creator)
        meta = _pop_meta(item)
        account_id = (item.get("account_id") or "").strip()
        if not account_id:
            return

        item["article_count"] = _to_int(item.get("article_count"))
        now_ts = utils.get_current_timestamp()

        async with get_session() as session:
            result = await session.execute(
                select(GzhAccount).where(GzhAccount.account_id == account_id)
            )
            row = result.scalars().first()
            if not row:
                item["add_ts"] = now_ts
                item["last_modify_ts"] = now_ts
                session.add(GzhAccount(**item))
            else:
                item["last_modify_ts"] = now_ts
                for key, value in item.items():
                    setattr(row, key, value)

            write_stats = bool(meta.get("_write_stats"))
            if write_stats and should_write_gzh_account_stats(account_id):
                session.add(
                    GzhAccountStats(
                        account_id=account_id,
                        sample_article_count=_to_int(meta.get("_sample_article_count")),
                        total_read_count=_to_int(meta.get("_total_read_count")),
                        total_like_count=_to_int(meta.get("_total_like_count")),
                        collected_at=collected_at_iso(),
                        scheduled_slot=resolve_scheduled_slot(),
                        source_type=meta.get("_source_type")
                        or crawler_type_var.get()
                        or "creator_crawl",
                    )
                )
            await session.commit()

    async def store_account_stats(self, stats_item: Dict):
        item = dict(stats_item)
        account_id = (item.get("account_id") or "").strip()
        if not account_id:
            return
        source_type = item.pop("_source_type", None) or crawler_type_var.get() or "creator_crawl"
        if not should_write_gzh_account_stats(account_id):
            return
        async with get_session() as session:
            session.add(
                GzhAccountStats(
                    account_id=account_id,
                    sample_article_count=_to_int(item.get("sample_article_count")),
                    total_read_count=_to_int(item.get("total_read_count")),
                    total_like_count=_to_int(item.get("total_like_count")),
                    collected_at=collected_at_iso(),
                    scheduled_slot=resolve_scheduled_slot(),
                    source_type=source_type,
                )
            )
            await session.commit()


class GzhSqliteStoreImplement(GzhDbStoreImplement):
    pass
