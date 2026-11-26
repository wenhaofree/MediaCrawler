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
from database.config_store import resolve_platform_cookie
from media_platform.gzh.weread_cli import (
    WereadCliError,
    WereadOmniBridge,
    biz_from_account_id,
    extract_biz_from_article_url,
    map_book_info_to_account,
    map_inspect_result_to_account,
    map_inspect_result_to_article,
    map_mobile_article,
    map_stats_article,
    merge_article_sources,
    normalize_account_id,
    validate_article_url,
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
        db_web_cookie = await resolve_platform_cookie("gzh")
        if db_web_cookie:
            self.bridge = WereadOmniBridge(web_cookie=db_web_cookie)
        utils.logger.info("[GzhCrawler.start] begin platform=gzh")
        if config.CRAWLER_TYPE == "creator":
            await self.get_accounts_and_articles()
        elif config.CRAWLER_TYPE == "search":
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            await self.get_specified_articles()
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

    async def get_specified_articles(self) -> None:
        article_urls: List[str] = list(getattr(config, "GZH_SPECIFIED_ID_LIST", []) or [])
        if not article_urls:
            utils.logger.error(
                "[GzhCrawler] GZH_SPECIFIED_ID_LIST is empty; set env or --specified_id"
            )
            return
        for raw_url in article_urls:
            try:
                await self.crawl_by_article_url(raw_url, fetch_articles=True)
            except Exception as exc:
                utils.logger.error(f"[GzhCrawler] article {raw_url} failed: {exc}")
            await asyncio.sleep(getattr(config, "GZH_REQUEST_INTERVAL_SEC", 1.5))

    async def get_accounts_and_articles(self) -> None:
        account_ids: List[str] = list(getattr(config, "GZH_ACCOUNT_IDS", []) or [])
        if not account_ids:
            utils.logger.error(
                "[GzhCrawler] GZH_ACCOUNT_IDS is empty; set env or --creator_id"
            )
            return
        for raw_id in account_ids:
            raw_text = str(raw_id or "").strip()
            if raw_text.startswith(("http://", "https://")):
                try:
                    await self.crawl_by_article_url(raw_text, fetch_articles=True)
                except Exception as exc:
                    utils.logger.error(f"[GzhCrawler] article url {raw_text} failed: {exc}")
                await asyncio.sleep(getattr(config, "GZH_REQUEST_INTERVAL_SEC", 1.5))
                continue
            try:
                account_id = normalize_account_id(raw_text)
            except ValueError as exc:
                utils.logger.error(f"[GzhCrawler] skip invalid id {raw_id}: {exc}")
                continue
            try:
                await self.crawl_one_account(account_id)
            except Exception as exc:
                utils.logger.error(f"[GzhCrawler] account {account_id} failed: {exc}")
            await asyncio.sleep(getattr(config, "GZH_REQUEST_INTERVAL_SEC", 1.5))

    async def resolve_account_from_article(
        self,
        article_url: str,
        *,
        enrich_book_info: bool = True,
    ) -> Dict:
        """Resolve official-account profile metadata from a strict WeChat article URL."""
        normalized_url = validate_article_url(article_url)
        biz_info = extract_biz_from_article_url(normalized_url)
        account_id = biz_info["account_id"]

        inspect_data: Dict = {}
        try:
            inspect_data = await self.bridge.inspect_article(normalized_url)
        except WereadCliError as exc:
            if "unknown command" not in str(exc).lower():
                raise
            utils.logger.warning(
                f"[GzhCrawler] inspect-article unsupported by CLI, falling back to __biz={biz_info['biz']}"
            )
            inspect_data = {
                "inputUrl": normalized_url,
                "source": "biz",
                "account": {
                    "accountId": account_id,
                    "biz": biz_info["biz"],
                    "bizNumericId": biz_info["biz_numeric_id"],
                },
                "article": {},
                "diagnostics": [],
            }

        book: Optional[Dict] = None
        if enrich_book_info:
            try:
                book = await self.bridge.book_info(account_id)
            except WereadCliError as exc:
                utils.logger.warning(
                    f"[GzhCrawler] book info unavailable for {account_id}: {exc}"
                )

        account_info = map_inspect_result_to_account(
            inspect_data,
            book,
            fallback_article_url=normalized_url,
        )
        article_info = map_inspect_result_to_article(
            inspect_data,
            account_id=account_info["account_id"],
            fallback_article_url=normalized_url,
        )
        return {
            "input_url": normalized_url,
            "source": inspect_data.get("source") or "biz",
            "account": account_info,
            "article": article_info,
            "diagnostics": inspect_data.get("diagnostics") or [],
        }

    async def crawl_by_article_url(
        self,
        article_url: str,
        *,
        fetch_articles: bool = False,
        max_articles: Optional[int] = None,
        write_account_stats: bool = True,
        source_type: Optional[str] = None,
    ) -> Dict:
        """Resolve official account from a strict article URL, save profile, and optionally crawl articles."""
        resolved = await self.resolve_account_from_article(
            article_url,
            enrich_book_info=True,
        )
        account = resolved["account"]
        account_id = account["account_id"]
        source = source_type or crawler_type_var.get() or "article_inspect"
        db_account_payload = {
            "account_id": account_id,
            "nickname": account.get("nickname") or "",
            "author": account.get("author") or "",
            "avatar": account.get("avatar") or "",
            "category": account.get("category") or "",
            "desc": account.get("desc") or "",
            "article_count": None,
        }

        if fetch_articles:
            result = await self.crawl_one_account(
                account_id,
                fetch_articles=True,
                max_articles=max_articles,
                write_account_stats=write_account_stats,
                source_type=source,
                fallback_account=db_account_payload,
            )
        else:
            await gzh_store.save_account(db_account_payload, write_stats=False, source_type=source)
            result = {
                **db_account_payload,
                "articles_saved": 0,
                "stats_saved": False,
                "warnings": [],
            }

        return {
            **result,
            "biz": account.get("biz"),
            "biz_numeric_id": account.get("biz_numeric_id"),
            "deep_link": account.get("deep_link"),
            "reader_link": account.get("reader_link"),
            "input_url": resolved["input_url"],
            "source": resolved["source"],
            "inspected_article": resolved.get("article"),
            "diagnostics": resolved.get("diagnostics") or [],
        }

    async def crawl_one_account(
        self,
        account_id: str,
        *,
        fetch_articles: bool = True,
        max_articles: Optional[int] = None,
        write_account_stats: bool = True,
        source_type: Optional[str] = None,
        fallback_account: Optional[Dict] = None,
    ) -> Dict:
        account_id = normalize_account_id(account_id)
        max_n = max_articles or getattr(config, "GZH_STATS_LIMIT", 20)
        source = source_type or crawler_type_var.get() or "creator_crawl"

        account_payload = dict(fallback_account) if fallback_account else {
            "account_id": account_id,
            "nickname": "",
            "author": "",
            "avatar": "",
            "category": "",
            "desc": "",
            "article_count": None,
        }
        account_payload["account_id"] = account_id
        try:
            book = await self.bridge.book_info(account_id)
            mapped_book = map_book_info_to_account(account_id, book)
            for key in ("nickname", "author", "avatar", "category", "desc"):
                if mapped_book.get(key) or not account_payload.get(key):
                    account_payload[key] = mapped_book.get(key) or account_payload.get(key) or ""
        except WereadCliError as exc:
            utils.logger.warning(
                f"[GzhCrawler] book info unavailable for {account_id}: {exc}"
            )

        await gzh_store.save_account(account_payload, write_stats=False, source_type=source)

        articles_saved = 0
        stats_saved = False
        warnings: List[str] = []
        if fetch_articles:
            fetch_n = max(1, min(100, int(max_n)))
            mobile_mapped: List[Dict] = []
            stats_mapped: List[Dict] = []

            try:
                mobile = await self.bridge.list_articles(account_id, count=fetch_n)
                for item in mobile.get("articles") or []:
                    mapped = map_mobile_article(account_id, item)
                    if not mapped.get("article_url") and mapped.get("review_id"):
                        try:
                            review = await self.bridge.review_single(mapped["review_id"])
                            if review.get("mpInfo"):
                                mapped = map_mobile_article(
                                    account_id,
                                    {
                                        **item,
                                        **review,
                                        "reviewId": review.get("reviewId") or mapped["review_id"],
                                    },
                                )
                            await asyncio.sleep(getattr(config, "GZH_REQUEST_INTERVAL_SEC", 1.5))
                        except WereadCliError as exc:
                            utils.logger.warning(
                                f"[GzhCrawler] article detail unavailable {mapped['review_id']}: {exc}"
                            )
                    if mapped.get("review_id") or mapped.get("original_id") or mapped.get("title"):
                        mobile_mapped.append(mapped)
            except WereadCliError as exc:
                msg = f"articles list failed: {exc}"
                warnings.append(msg)
                utils.logger.warning(f"[GzhCrawler] {account_id}: {msg}")

            try:
                stats = await self.bridge.article_stats(account_id, limit=fetch_n)
                if stats.get("accountName") and not account_payload.get("nickname"):
                    account_payload["nickname"] = stats.get("accountName") or ""
                for item in stats.get("articles") or []:
                    mapped = map_stats_article(account_id, item)
                    if mapped.get("review_id") or mapped.get("original_id") or mapped.get("title"):
                        stats_mapped.append(mapped)
            except WereadCliError as exc:
                msg = f"article-stats failed (check WEREAD_WEB_COOKIE): {exc}"
                warnings.append(msg)
                utils.logger.warning(f"[GzhCrawler] {account_id}: {msg}")

            merged = merge_article_sources(mobile_mapped, stats_mapped)
            # Keep source articles even when the Web-only stats endpoint is unavailable.
            to_save = merged
            stats_article_count = sum(
                1 for mapped in to_save if mapped.get("read_count") is not None
            )

            total_read = 0
            total_like = 0
            with_cover = 0
            for mapped in to_save:
                await gzh_store.upsert_article(mapped)
                articles_saved += 1
                total_read += int(mapped.get("read_count") or 0)
                total_like += int(mapped.get("like_count") or 0)
                if mapped.get("cover_url"):
                    with_cover += 1

            if stats_mapped:
                stats_saved = True
                if write_account_stats:
                    await gzh_store.save_account(
                        {
                            **account_payload,
                            "article_count": len(to_save),
                        },
                        write_stats=True,
                        sample_article_count=stats_article_count,
                        total_read_count=total_read,
                        total_like_count=total_like,
                        source_type=source,
                    )
            utils.logger.info(
                f"[GzhCrawler] {account_id} saved={articles_saved} with_cover={with_cover} "
                f"mobile={len(mobile_mapped)} stats={len(stats_mapped)}"
            )

        return {
            "account_id": account_id,
            "nickname": account_payload.get("nickname"),
            "author": account_payload.get("author"),
            "avatar": account_payload.get("avatar"),
            "category": account_payload.get("category"),
            "desc": account_payload.get("desc"),
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
