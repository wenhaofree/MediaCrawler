# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/douyin/core.py
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

import asyncio
import os
import random
from asyncio import Task
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from database.db_session import get_session
from database.models import DouyinAweme, DouyinAwemeStats
from media_downloader import MediaDownloader
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from sqlalchemy import func, select
from store import douyin as douyin_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from tools.httpx_util import make_async_client
from var import (
    crawler_type_var,
    dy_scheduled_slot_var,
    dy_source_type_var,
    dy_write_aweme_stats_var,
    dy_write_creator_stats_var,
    source_keyword_var,
)

from . import media as douyin_media
from .client import DouYinClient
from .exception import DataFetchError
from .field import PublishTimeType
from .help import (
    parse_video_info_from_url,
    parse_creator_info_from_url,
    get_web_id,
    generate_ms_token,
)
from .lifecycle import (
    SLOT_MANUAL,
    filter_aweme_rows_for_slot,
    resolve_scheduled_slot,
    should_write_creator_stats,
)
from .login import DouYinLogin


class DouYinCrawler(AbstractCrawler):
    context_page: Optional[Page]
    dy_client: DouYinClient
    browser_context: Optional[BrowserContext]
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.douyin.com"
        self.cookie_urls = [
            "https://douyin.com",
            self.index_url,
            "https://creator.douyin.com",
            "https://douhot.douyin.com",
            "https://live.douyin.com",
        ]
        self.context_page = None
        self.browser_context = None
        self.cdp_manager = None
        self.ip_proxy_pool = None  # Proxy IP pool for automatic proxy refresh
        self._media_downloader: Optional[MediaDownloader] = None

    async def init_pure_api_session(self, proxy: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Initialize guest cookies and headers via HTTP handshake without browser.
        If config.COOKIES is provided, it merges user cookies.
        """
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        cookie_dict: Dict[str, str] = {}

        # 1. Parse configured cookies if provided
        if config.COOKIES:
            cookie_dict.update(utils.convert_str_cookie_to_dict(config.COOKIES))

        # 2. HTTP handshake to get initial guest cookies (ttwid, passport_csrf_token, etc.)
        try:
            async with make_async_client(proxy=proxy) as client:
                resp = await client.get(
                    self.index_url,
                    headers={"User-Agent": user_agent},
                    follow_redirects=True,
                    timeout=10,
                )
                for k, v in resp.cookies.items():
                    cookie_dict.setdefault(k, v)
        except Exception as exc:
            utils.logger.warning(f"[DouYinCrawler.init_pure_api_session] Handshake warning: {exc}")

        # 3. Ensure essential Douyin client identifiers
        cookie_dict.setdefault("webid", get_web_id())
        cookie_dict.setdefault("msToken", generate_ms_token())

        cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
        return cookie_str, cookie_dict

    async def start_pure_api(self, httpx_proxy_format: Optional[str]) -> None:
        cookie_str, cookie_dict = await self.init_pure_api_session(httpx_proxy_format)
        if not config.COOKIES:
            utils.logger.info(
                "[DouYinCrawler.start_pure_api] 未提供 --cookies，已通过访客会话握手初始化凭据。"
                "若目标接口有登录权限限制，可通过 --cookies 传入有效 Cookie。"
            )
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        headers = {
            "User-Agent": user_agent,
            "Cookie": cookie_str,
            "Host": "www.douyin.com",
            "Origin": "https://www.douyin.com/",
            "Referer": "https://www.douyin.com/",
            "Content-Type": "application/json;charset=UTF-8",
        }
        self.dy_client = DouYinClient(
            headers=headers,
            playwright_page=None,
            cookie_dict=cookie_dict,
            proxy=httpx_proxy_format,
            proxy_ip_pool=self.ip_proxy_pool,
        )

        crawler_type_var.set(config.CRAWLER_TYPE)
        if config.CRAWLER_TYPE == "search":
            # Search for notes and retrieve their comment information.
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            # Get the information and comments of the specified post
            await self.get_specified_awemes()
        elif config.CRAWLER_TYPE == "creator":
            # Get the information and comments of the specified creator
            await self.get_creators_and_videos()

        utils.logger.info("[DouYinCrawler.start_pure_api] Douyin Pure API Crawler finished ...")

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        if getattr(config, "ENABLE_PURE_API_MODE", False):
            utils.logger.info("[DouYinCrawler] 启用纯 API 模式 (无浏览器/无 Playwright/无需 9222 端口)")
            await self.start_pure_api(httpx_proxy_format)
            return

        async with async_playwright() as playwright:
            # Select startup mode based on configuration
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[DouYinCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    None,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[DouYinCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
                # stealth.min.js is a js script to prevent the website from detecting the crawler.
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.dy_client = await self.create_douyin_client(httpx_proxy_format)
            if not await self.dy_client.pong(browser_context=self.browser_context):
                if config.CDP_ATTACH_ONLY:
                    raise RuntimeError(
                        "Douyin is not logged in on the attached 9222 browser, and attach-only mode forbids QR login."
                    )
                login_obj = DouYinLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # you phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(
                    browser_context=self.browser_context,
                    urls=self.cookie_urls,
                )
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                # Get the information and comments of the specified creator
                await self.get_creators_and_videos()

            utils.logger.info("[DouYinCrawler.start] Douyin Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[DouYinCrawler.search] Begin search douyin keywords")
        dy_limit_count = 10  # douyin limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < dy_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = dy_limit_count
        start_page = config.START_PAGE  # start page number
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[DouYinCrawler.search] Current keyword: {keyword}")
            aweme_list: List[str] = []
            page = 0
            dy_search_id = ""
            while (page - start_page + 1) * dy_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[DouYinCrawler.search] Skip {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page}")
                    posts_res = await self.dy_client.search_info_by_keyword(
                        keyword=keyword,
                        offset=page * dy_limit_count - dy_limit_count,
                        publish_time=PublishTimeType(config.PUBLISH_TIME_TYPE),
                        search_id=dy_search_id,
                    )
                    if posts_res.get("data") is None or posts_res.get("data") == []:
                        utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page} is empty,{posts_res.get('data')}`")
                        break
                except DataFetchError:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed")
                    break

                page += 1
                if "data" not in posts_res:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed，账号也许被风控了。")
                    break
                dy_search_id = posts_res.get("extra", {}).get("logid", "")
                page_aweme_list = []
                for post_item in posts_res.get("data"):
                    try:
                        aweme_info: Dict = (post_item.get("aweme_info") or post_item.get("aweme_mix_info", {}).get("mix_items")[0])
                    except TypeError:
                        continue
                    aweme_list.append(aweme_info.get("aweme_id", ""))
                    page_aweme_list.append(aweme_info.get("aweme_id", ""))
                    await douyin_store.update_douyin_aweme(aweme_item=aweme_info)
                    await self.download_media(aweme_item=aweme_info)
                
                # Batch get note comments for the current page
                await self.batch_get_note_comments(page_aweme_list)

                # Sleep after each page navigation
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[DouYinCrawler.search] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")
            utils.logger.info(f"[DouYinCrawler.search] keyword:{keyword}, aweme_list:{aweme_list}")

    async def get_specified_awemes(self):
        """Get the information and comments of the specified post from URLs or IDs"""
        utils.logger.info("[DouYinCrawler.get_specified_awemes] Parsing video URLs...")
        aweme_id_list = []
        for video_url in config.DY_SPECIFIED_ID_LIST:
            try:
                video_info = parse_video_info_from_url(video_url)

                # Handling short links
                if video_info.url_type == "short":
                    utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Resolving short link: {video_url}")
                    resolved_url = await self.dy_client.resolve_short_url(video_url)
                    if resolved_url:
                        # Extract video ID from parsed URL
                        video_info = parse_video_info_from_url(resolved_url)
                        utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Short link resolved to aweme ID: {video_info.aweme_id}")
                    else:
                        utils.logger.error(f"[DouYinCrawler.get_specified_awemes] Failed to resolve short link: {video_url}")
                        continue

                aweme_id_list.append(video_info.aweme_id)
                utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Parsed aweme ID: {video_info.aweme_id} from {video_url}")
            except ValueError as e:
                utils.logger.error(f"[DouYinCrawler.get_specified_awemes] Failed to parse video URL: {e}")
                continue

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore) for aweme_id in aweme_id_list]
        aweme_details = await asyncio.gather(*task_list)
        for aweme_detail in aweme_details:
            if aweme_detail is not None:
                await douyin_store.update_douyin_aweme(aweme_item=aweme_detail)
                await self.download_media(aweme_item=aweme_detail)
        await self.batch_get_note_comments(aweme_id_list)

    async def get_aweme_detail(self, aweme_id: str, semaphore: asyncio.Semaphore) -> Any:
        """Get note detail"""
        async with semaphore:
            try:
                result = await self.dy_client.get_video_by_id(aweme_id)
                # Sleep after fetching aweme detail
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[DouYinCrawler.get_aweme_detail] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching aweme {aweme_id}")
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] Get aweme detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] have not fund note detail aweme_id:{aweme_id}, err: {ex}")
                return None
            except Exception as ex:
                utils.logger.exception(
                    f"[DouYinCrawler.get_aweme_detail] unexpected error for aweme_id:{aweme_id}"
                )
                return None

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        """
        Batch get note comments
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for aweme_id in aweme_list:
            task = asyncio.create_task(self.get_comments(aweme_id, semaphore), name=aweme_id)
            task_list.append(task)
        if len(task_list) > 0:
            await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            try:
                # Pass the list of keywords to the get_aweme_all_comments method
                # Use fixed crawling interval
                crawl_interval = config.CRAWLER_MAX_SLEEP_SEC
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=crawl_interval,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=douyin_store.batch_update_dy_aweme_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
                # Sleep after fetching comments
                await asyncio.sleep(crawl_interval)
                utils.logger.info(f"[DouYinCrawler.get_comments] Sleeping for {crawl_interval} seconds after fetching comments for aweme {aweme_id}")
                utils.logger.info(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} comments have all been obtained and filtered ...")
            except DataFetchError as e:
                utils.logger.error(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} get comments failed, error: {e}")

    async def get_creators_and_videos(self) -> None:
        """
        Get the information and videos of the specified creator from URLs or IDs
        """
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Begin get douyin creators")
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Parsing creator URLs...")
        slot = resolve_scheduled_slot(getattr(config, "DY_SCHEDULED_SLOT", SLOT_MANUAL))
        write_creator_stats = should_write_creator_stats(slot)
        dy_scheduled_slot_var.set(slot)
        dy_write_creator_stats_var.set(write_creator_stats)
        utils.logger.info(
            f"[DouYinCrawler.get_creators_and_videos] scheduled_slot={slot}, write_creator_stats={write_creator_stats}"
        )

        for creator_url in config.DY_CREATOR_ID_LIST:
            try:
                creator_info_parsed = parse_creator_info_from_url(creator_url)
                user_id = creator_info_parsed.sec_user_id
                utils.logger.info(f"[DouYinCrawler.get_creators_and_videos] Parsed sec_user_id: {user_id} from {creator_url}")
            except ValueError as e:
                utils.logger.error(f"[DouYinCrawler.get_creators_and_videos] Failed to parse creator URL: {e}")
                continue

            try:
                creator_info: Dict = await self.dy_client.get_user_info(user_id)
                if creator_info:
                    dy_source_type_var.set("creator_crawl")
                    await douyin_store.save_creator(
                        user_id,
                        creator=creator_info,
                        write_stats=write_creator_stats,
                        source_type="creator_crawl",
                        scheduled_slot=slot,
                    )
            except DataFetchError as ex:
                utils.logger.warning(
                    f"[DouYinCrawler.get_creators_and_videos] Could not fetch creator profile for {user_id}: {ex}. Proceeding to fetch videos..."
                )

            # Discover posts, then refresh stats by lifecycle (non-manual slots)
            try:
                if slot == SLOT_MANUAL:
                    all_video_list = await self.dy_client.get_all_user_aweme_posts(
                        sec_user_id=user_id,
                        callback=self.fetch_creator_video_detail,
                    )
                    video_ids = [video_item.get("aweme_id") for video_item in all_video_list]
                else:
                    await self.dy_client.get_all_user_aweme_posts(
                        sec_user_id=user_id,
                        callback=self.discover_creator_awemes,
                    )
                    candidate_ids = await self.select_lifecycle_aweme_ids(user_id, slot)
                    utils.logger.info(
                        f"[DouYinCrawler.get_creators_and_videos] lifecycle candidates for {user_id}: {len(candidate_ids)}"
                    )
                    await self.refresh_aweme_stats_by_ids(candidate_ids, source_type="detail")
                    video_ids = candidate_ids
            except DataFetchError as ex:
                utils.logger.error(
                    f"[DouYinCrawler.get_creators_and_videos] Failed to fetch creator videos for sec_user_id:{user_id}, err: {ex}"
                )
                continue

            await self.batch_get_note_comments(video_ids)

    async def discover_creator_awemes(self, video_list: List[Dict]):
        """Upsert aweme base rows from post list without detail round-trips (lifecycle mode)."""
        dy_source_type_var.set("creator_crawl")
        for post_item in video_list:
            if not post_item or not post_item.get("aweme_id"):
                continue
            await douyin_store.update_douyin_aweme(
                aweme_item=post_item,
                source_type="creator_crawl",
                write_stats=False,
            )
            await self.download_media(aweme_item=post_item)

    async def select_lifecycle_aweme_ids(self, sec_uid: str, slot: str) -> List[str]:
        """Pick local aweme IDs that should receive a stats refresh for this slot."""
        rows: List[Dict[str, Any]] = []
        save_option = getattr(config, "SAVE_DATA_OPTION", "")
        if save_option not in {"sqlite", "db", "mysql", "postgres"}:
            return []
        try:
            async with get_session() as session:
                if session is None:
                    return []
                aweme_result = await session.execute(
                    select(DouyinAweme.aweme_id, DouyinAweme.create_time).where(
                        DouyinAweme.sec_uid == sec_uid
                    )
                )
                awemes = aweme_result.all()
                if not awemes:
                    return []
                stats_result = await session.execute(
                    select(
                        DouyinAwemeStats.aweme_id,
                        func.max(DouyinAwemeStats.collected_at).label("last_collected_at"),
                    ).group_by(DouyinAwemeStats.aweme_id)
                )
                last_map = {row.aweme_id: row.last_collected_at for row in stats_result.all()}
                rows = [
                    {
                        "aweme_id": aweme.aweme_id,
                        "create_time": aweme.create_time,
                        "last_collected_at": last_map.get(aweme.aweme_id),
                    }
                    for aweme in awemes
                ]
        except Exception as ex:
            utils.logger.exception(
                f"[DouYinCrawler.select_lifecycle_aweme_ids] failed for sec_uid={sec_uid}: {ex}"
            )
            return []
        return filter_aweme_rows_for_slot(rows, slot)

    async def refresh_aweme_stats_by_ids(self, aweme_ids: List[str], source_type: str = "detail") -> None:
        if not aweme_ids:
            return
        dy_source_type_var.set(source_type)
        dy_write_aweme_stats_var.set(True)
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore) for aweme_id in aweme_ids]
        note_details = await asyncio.gather(*task_list, return_exceptions=True)
        for aweme_id, aweme_item in zip(aweme_ids, note_details):
            if isinstance(aweme_item, Exception):
                utils.logger.error(
                    f"[DouYinCrawler.refresh_aweme_stats_by_ids] Failed aweme_id:{aweme_id}, err: {aweme_item}"
                )
                continue
            if aweme_item is not None:
                await douyin_store.update_douyin_aweme(
                    aweme_item=aweme_item,
                    source_type=source_type,
                    write_stats=True,
                )
                await self.download_media(aweme_item=aweme_item)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data (manual / full mode).
        """
        dy_source_type_var.set("detail")
        dy_write_aweme_stats_var.set(True)
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(post_item.get("aweme_id"), semaphore) for post_item in video_list]

        note_details = await asyncio.gather(*task_list, return_exceptions=True)
        for post_item, aweme_item in zip(video_list, note_details):
            if isinstance(aweme_item, Exception):
                utils.logger.error(
                    f"[DouYinCrawler.fetch_creator_video_detail] Failed to fetch aweme detail for aweme_id:{post_item.get('aweme_id')}, err: {aweme_item}"
                )
                continue
            if aweme_item is not None:
                await douyin_store.update_douyin_aweme(
                    aweme_item=aweme_item,
                    source_type="detail",
                    write_stats=True,
                )
                await self.download_media(aweme_item=aweme_item)

    async def create_douyin_client(self, httpx_proxy: Optional[str]) -> DouYinClient:
        """Create douyin client"""
        cookie_str, cookie_dict = await utils.convert_browser_context_cookies(
            self.browser_context,
            urls=self.cookie_urls,
        )  # type: ignore
        douyin_client = DouYinClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Host": "www.douyin.com",
                "Origin": "https://www.douyin.com/",
                "Referer": "https://www.douyin.com/",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,  # Pass proxy pool for automatic refresh
        )
        return douyin_client

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={
                    "width": 1920,
                    "height": 1080
                },
                user_agent=user_agent,
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        使用CDP模式启动浏览器
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            # Add anti-detection script
            await self.cdp_manager.add_stealth_script()

            # Show browser information
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[DouYinCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[DouYinCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # Fall back to standard mode
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        """Close browser context"""
        # If you use CDP mode, special processing is required
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[DouYinCrawler.close] Browser context closed ...")

    async def download_media(self, aweme_item: Dict) -> None:
        """下载抖音作品的媒体资源（图集图片，或视频 + 封面）

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEDIA:
            return
        try:
            items = douyin_media.build_media_items(aweme_item)
            if items:
                await self._get_media_downloader().download_all(items)
        except Exception as exc:
            # 媒体下载是旁路能力，解析异常/网络异常都不能中断爬取主流程
            utils.logger.error(f"[DouYinCrawler.download_media] 媒体下载异常: {exc}")

    def _get_media_downloader(self) -> MediaDownloader:
        """惰性创建媒体下载器，并同步最新的代理与 UA（代理池是就地刷新的）"""
        if self._media_downloader is None:
            self._media_downloader = MediaDownloader(
                platform="dy",
                proxy=getattr(self.dy_client, "proxy", None),
                extra_headers=self._media_headers(),
            )
        else:
            self._media_downloader.update_credentials(
                proxy=getattr(self.dy_client, "proxy", None),
                extra_headers=self._media_headers(),
            )
        return self._media_downloader

    def _media_headers(self) -> Dict:
        """媒体请求头：平台 Referer（防盗链）+ UA。

        client.headers 里含 Cookie，不能整体透传到 CDN 请求上，因此只取 UA。
        """
        headers = {"Referer": "https://www.douyin.com/"}
        client_headers = getattr(self.dy_client, "headers", {}) or {}
        if client_headers.get("User-Agent"):
            headers["User-Agent"] = client_headers["User-Agent"]
        return headers
