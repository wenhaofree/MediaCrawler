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


def _norm_id(value: Any) -> str:
    return str(value or "").strip()


def _prefer_review_id(existing: str, incoming: str) -> str:
    """Prefer stats-style review_id that embeds originalId (usually longer / contains WR)."""
    existing = _norm_id(existing)
    incoming = _norm_id(incoming)
    if not existing:
        return incoming
    if not incoming:
        return existing
    if incoming == existing:
        return existing
    score_e = (1 if "_WR" in existing else 0) + (1 if existing.count("_") >= 2 else 0) + len(existing) / 1000.0
    score_i = (1 if "_WR" in incoming else 0) + (1 if incoming.count("_") >= 2 else 0) + len(incoming) / 1000.0
    return incoming if score_i >= score_e else existing


def _prefer_text(existing: Any, incoming: Any) -> Any:
    incoming_s = (incoming or "").strip() if isinstance(incoming, str) else incoming
    if incoming_s not in (None, ""):
        return incoming
    return existing


async def _find_existing_article(session, review_id: str, original_id: str, account_id: str, title: str, published_at: Optional[int]):
    """
    Resolve one logical article across mobile/stats ID schemes:
    1) review_id exact
    2) original_id exact (non-empty)
    3) account_id + title + published_at
    4) account_id + title (fallback when published_at missing on either side)
    """
    if review_id:
        result = await session.execute(
            select(GzhArticle).where(GzhArticle.review_id == review_id)
        )
        row = result.scalars().first()
        if row:
            return row

    if original_id:
        result = await session.execute(
            select(GzhArticle).where(GzhArticle.original_id == original_id)
        )
        row = result.scalars().first()
        if row:
            return row
        # stats review_id often equals accountId + '_' + originalId
        if account_id:
            composed = f"{account_id}_{original_id}"
            result = await session.execute(
                select(GzhArticle).where(GzhArticle.review_id == composed)
            )
            row = result.scalars().first()
            if row:
                return row

    title = (title or "").strip()
    if account_id and title:
        if published_at is not None:
            result = await session.execute(
                select(GzhArticle).where(
                    GzhArticle.account_id == account_id,
                    GzhArticle.title == title,
                    GzhArticle.published_at == published_at,
                )
            )
            row = result.scalars().first()
            if row:
                return row
        result = await session.execute(
            select(GzhArticle).where(
                GzhArticle.account_id == account_id,
                GzhArticle.title == title,
            )
        )
        rows = list(result.scalars().all())
        if len(rows) == 1:
            return rows[0]
        if published_at is not None:
            for row in rows:
                if row.published_at in (None, published_at):
                    return row
        if rows:
            # Prefer the row that already has engagement / original_id
            rows.sort(
                key=lambda r: (
                    1 if r.read_count is not None else 0,
                    1 if (r.original_id or "") else 0,
                    r.id or 0,
                ),
                reverse=True,
            )
            return rows[0]
    return None


class GzhDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        item = dict(content_item)
        review_id = _norm_id(item.get("review_id"))
        original_id = _norm_id(item.get("original_id")) or None
        account_id = _norm_id(item.get("account_id"))
        title = (item.get("title") or "").strip()
        if not review_id and not original_id:
            return
        if not review_id and original_id:
            review_id = f"{account_id}_{original_id}" if account_id else original_id

        item["read_count"] = _to_int(item.get("read_count"))
        item["like_count"] = _to_int(item.get("like_count"))
        item["published_at"] = _to_int(item.get("published_at"))

        async with get_session() as session:
            row = await _find_existing_article(
                session,
                review_id=review_id,
                original_id=original_id or "",
                account_id=account_id,
                title=title,
                published_at=item.get("published_at"),
            )

            now_ts = utils.get_current_timestamp()
            if not row:
                payload = {
                    "review_id": review_id,
                    "original_id": original_id,
                    "account_id": account_id,
                    "title": title,
                    "summary": item.get("summary") or "",
                    "account_name": item.get("account_name") or "",
                    "article_url": item.get("article_url") or "",
                    "cover_url": item.get("cover_url") or "",
                    "published_at": item.get("published_at"),
                    "read_count": item.get("read_count"),
                    "like_count": item.get("like_count"),
                    "add_ts": now_ts,
                    "last_modify_ts": now_ts,
                }
                session.add(GzhArticle(**payload))
            else:
                # Merge into one row; keep a stable preferred review_id / original_id.
                merged_review = _prefer_review_id(row.review_id, review_id)
                # If preferred review_id belongs to another row, keep existing to avoid unique conflict.
                if merged_review != row.review_id:
                    clash = await session.execute(
                        select(GzhArticle).where(
                            GzhArticle.review_id == merged_review,
                            GzhArticle.id != row.id,
                        )
                    )
                    if clash.scalars().first():
                        merged_review = row.review_id

                row.review_id = merged_review
                if original_id:
                    row.original_id = original_id
                elif not row.original_id:
                    row.original_id = None
                if account_id:
                    row.account_id = account_id
                row.title = _prefer_text(row.title, title) or row.title
                row.summary = _prefer_text(row.summary, item.get("summary"))
                row.account_name = _prefer_text(row.account_name, item.get("account_name"))
                row.article_url = _prefer_text(row.article_url, item.get("article_url"))
                row.cover_url = _prefer_text(row.cover_url, item.get("cover_url"))
                if item.get("published_at") is not None:
                    row.published_at = item["published_at"]
                if item.get("read_count") is not None:
                    row.read_count = item["read_count"]
                if item.get("like_count") is not None:
                    row.like_count = item["like_count"]
                row.last_modify_ts = now_ts
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

    async def delete_articles_without_read(self, account_id: str) -> int:
        account_id = (account_id or "").strip()
        if not account_id:
            return 0
        async with get_session() as session:
            result = await session.execute(
                select(GzhArticle).where(
                    GzhArticle.account_id == account_id,
                    GzhArticle.read_count.is_(None),
                )
            )
            rows = list(result.scalars().all())
            for row in rows:
                await session.delete(row)
            await session.commit()
            return len(rows)


class GzhSqliteStoreImplement(GzhDbStoreImplement):
    pass
