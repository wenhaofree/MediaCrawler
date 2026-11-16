# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from __future__ import annotations

from typing import Any, Dict, Optional

import config
from tools import utils

from ._store_impl import GzhDbStoreImplement, GzhSqliteStoreImplement


class GzhStoreFactory:
    STORES = {
        "db": GzhDbStoreImplement,
        "postgres": GzhDbStoreImplement,
        "sqlite": GzhSqliteStoreImplement,
    }

    @staticmethod
    def create_store():
        store_class = GzhStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[GzhStoreFactory] SAVE_DATA_OPTION must be db/postgres/sqlite for gzh"
            )
        return store_class()


async def save_account(
    account: Dict[str, Any],
    *,
    write_stats: bool = False,
    sample_article_count: Optional[int] = None,
    total_read_count: Optional[int] = None,
    total_like_count: Optional[int] = None,
    source_type: Optional[str] = None,
) -> None:
    payload = dict(account)
    if sample_article_count is not None:
        payload["article_count"] = sample_article_count
    payload["_write_stats"] = write_stats
    if sample_article_count is not None:
        payload["_sample_article_count"] = sample_article_count
    if total_read_count is not None:
        payload["_total_read_count"] = total_read_count
    if total_like_count is not None:
        payload["_total_like_count"] = total_like_count
    if source_type:
        payload["_source_type"] = source_type
    utils.logger.info(
        f"[store.gzh.save_account] account_id={payload.get('account_id')} "
        f"nickname={payload.get('nickname')}"
    )
    await GzhStoreFactory.create_store().store_creator(payload)


async def upsert_article(article: Dict[str, Any]) -> None:
    if not article.get("review_id") and not article.get("original_id"):
        utils.logger.warning("[store.gzh.upsert_article] skip article without id")
        return
    await GzhStoreFactory.create_store().store_content(article)


async def save_account_stats_snapshot(
    account_id: str,
    *,
    sample_article_count: int,
    total_read_count: int,
    total_like_count: int,
    source_type: Optional[str] = None,
) -> None:
    await GzhStoreFactory.create_store().store_account_stats(
        {
            "account_id": account_id,
            "sample_article_count": sample_article_count,
            "total_read_count": total_read_count,
            "total_like_count": total_like_count,
            "_source_type": source_type,
        }
    )


async def delete_articles_without_read(account_id: str) -> int:
    """Remove legacy mobile-only rows that never got read/like enrichment."""
    store = GzhStoreFactory.create_store()
    if hasattr(store, "delete_articles_without_read"):
        return await store.delete_articles_without_read(account_id)
    return 0
