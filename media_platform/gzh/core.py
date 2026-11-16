# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from playwright.async_api import BrowserContext, BrowserType

import config
from base.base_crawler import AbstractCrawler
from media_platform.gzh.weread_cli import (
    WereadCliError,
    WereadOmniBridge,
    map_book_info_to_account,
    map_mobile_article,
    map_stats_article,
    normalize_account_id,
)
from store import gzh as gzh_store
from tools import utils
from var import crawler_type_var, reset_gzh_account_stats_seen


class GzhCrawler(AbstractCrawler):
    """WeChat official-account crawler driven by weread-omni CLI."""

    def __init__(self) -> None:
        self.bridge = WereadOmniBridge()

    async def start(self) -> None:
        crawler_type_var.set(config.CRAWLER_TYPE)
        reset_gzh_account_stats_seen()
        utils.logger.info("[GzhCrawler.start] begin platform=gzh")
        if config.CRAWLER_TYPE == "creator":
            await self.get_accounts_and_articles()
        elif config.CRAWLER_TYPE == "search":
            await self.search()
        else:
            utils.logger.warning(
                f"[GzhCrawler.start] unsupported crawler type: {config.CRAWLER_TYPE}; use creator"
            )
            await self.get_accounts_and_articles()
        utils.logger.info("[GzhCrawler.start] finished")

    async def search(self) -> None:
        keyword = (config.KEYWORDS or "").split(",")[0].strip()
        if not keyword:
            utils.logger.warning("[GzhCrawler.search] KEYWORDS empty")
            return
        try:
            books = await self.bridge.search_accounts(keyword, count=10)
        except WereadCliError as exc:
            utils.logger.error(f"[GzhCrawler.search] failed: {exc}")
            return
        for book in books:
            account_id = book.get("bookId") or book.get("accountId")
            if not account_id:
                continue
            await self.crawl_one_account(str(account_id))
            await asyncio.sleep(getattr(config, "GZH_REQUEST_INTERVAL_SEC", 1.5))

    async def get_accounts_and_articles(self) -> None:
        account_ids: List[str] = list(getattr(config, "GZH_ACCOUNT_IDS", []) or [])
        if not account_ids:
            utils.logger.error(
                "[GzhCrawler] GZH_ACCOUNT_IDS is empty; set env or --creator_id"
            )
            return
        for raw_id in account_ids:
            try:
                account_id = normalize_account_id(raw_id)
            except ValueError as exc:
                utils.logger.error(f"[GzhCrawler] skip invalid id {raw_id}: {exc}")
                continue
            try:
                await self.crawl_one_account(account_id)
            except Exception as exc:
                utils.logger.error(f"[GzhCrawler] account {account_id} failed: {exc}")
            await asyncio.sleep(getattr(config, "GZH_REQUEST_INTERVAL_SEC", 1.5))

    async def crawl_one_account(
        self,
        account_id: str,
        *,
        fetch_articles: bool = True,
        max_articles: Optional[int] = None,
        write_account_stats: bool = True,
        source_type: Optional[str] = None,
    ) -> Dict:
        account_id = normalize_account_id(account_id)
        max_n = max_articles or getattr(config, "GZH_STATS_LIMIT", 20)
        source = source_type or crawler_type_var.get() or "creator_crawl"

        account_payload = {
            "account_id": account_id,
            "nickname": "",
            "author": "",
            "avatar": "",
            "category": "",
            "desc": "",
            "article_count": None,
        }
        try:
            book = await self.bridge.book_info(account_id)
            account_payload = map_book_info_to_account(account_id, book)
        except WereadCliError as exc:
            utils.logger.warning(
                f"[GzhCrawler] book info unavailable for {account_id}: {exc}"
            )

        await gzh_store.save_account(account_payload, write_stats=False, source_type=source)

        articles_saved = 0
        stats_saved = False
        warnings: List[str] = []
        if fetch_articles:
            try:
                mobile = await self.bridge.list_articles(
                    account_id, count=min(max_n, getattr(config, "GZH_ARTICLES_COUNT", 20))
                )
                for item in mobile.get("articles") or []:
                    mapped = map_mobile_article(account_id, item)
                    if mapped.get("review_id") or mapped.get("original_id"):
                        await gzh_store.upsert_article(mapped)
                        articles_saved += 1
            except WereadCliError as exc:
                msg = f"articles list failed: {exc}"
                warnings.append(msg)
                utils.logger.warning(f"[GzhCrawler] {account_id}: {msg}")

            total_read = 0
            total_like = 0
            sample_count = 0
            try:
                stats = await self.bridge.article_stats(account_id, limit=max_n)
                if stats.get("accountName") and not account_payload.get("nickname"):
                    account_payload["nickname"] = stats.get("accountName") or ""
                for item in stats.get("articles") or []:
                    mapped = map_stats_article(account_id, item)
                    if not (mapped.get("review_id") or mapped.get("original_id")):
                        continue
                    await gzh_store.upsert_article(mapped)
                    sample_count += 1
                    total_read += int(mapped.get("read_count") or 0)
                    total_like += int(mapped.get("like_count") or 0)
                if sample_count:
                    articles_saved = max(articles_saved, sample_count)
                    if write_account_stats:
                        await gzh_store.save_account(
                            {
                                **account_payload,
                                "article_count": sample_count,
                            },
                            write_stats=True,
                            sample_article_count=sample_count,
                            total_read_count=total_read,
                            total_like_count=total_like,
                            source_type=source,
                        )
                        stats_saved = True
            except WereadCliError as exc:
                msg = (
                    f"article-stats failed (check WEREAD_WEB_COOKIE): {exc}"
                )
                warnings.append(msg)
                utils.logger.warning(f"[GzhCrawler] {account_id}: {msg}")

        return {
            "account_id": account_id,
            "nickname": account_payload.get("nickname"),
            "articles_saved": articles_saved,
            "stats_saved": stats_saved,
            "warnings": warnings,
        }

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        raise RuntimeError("gzh crawler uses weread-omni CLI and does not launch a browser")
