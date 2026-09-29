# -*- coding: utf-8 -*-

import asyncio
import os
import random
from typing import Dict, Optional

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import qimai as qimai_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import QimaiClient
from .login import QimaiLogin


class QimaiCrawler(AbstractCrawler):
    context_page: Page
    qimai_client: QimaiClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.qimai.cn"
        self.cookie_urls = [self.index_url, "https://api.qimai.cn"]
        self.user_agent = utils.get_user_agent()
        self.cdp_manager = None

    async def start(self) -> None:
        playwright_proxy_format = None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, _ = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            if config.ENABLE_CDP_MODE:
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.CDP_HEADLESS,
                )
            else:
                self.browser_context = await self.launch_browser(
                    playwright.chromium,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.HEADLESS,
                )

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url, wait_until="domcontentloaded")
            if config.LOGIN_TYPE == "cookie" and config.COOKIES:
                await QimaiLogin(
                    login_type=config.LOGIN_TYPE,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                ).begin()

            self.qimai_client = QimaiClient(
                playwright_page=self.context_page,
                headers={"User-Agent": self.user_agent, "Cookie": ""},
            )
            await self.qimai_client.update_cookies(self.browser_context, self.cookie_urls)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_apps()
            elif config.CRAWLER_TYPE == "rank":
                await self.rank()
            else:
                utils.logger.info("[QimaiCrawler.start] Qimai supports search, detail and rank")

            utils.logger.info("[QimaiCrawler.start] Qimai crawler finished")

    async def search(self) -> None:
        for keyword in config.KEYWORDS.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue
            source_keyword_var.set(keyword)
            apps = await self.qimai_client.search_apps(keyword)
            await qimai_store.batch_update_qimai_apps(apps[: config.CRAWLER_MAX_NOTES_COUNT])
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

    async def get_specified_apps(self) -> None:
        for app_id in config.QIMAI_SPECIFIED_ID_LIST:
            source_keyword_var.set(app_id)
            apps = await self.qimai_client.get_app_detail(app_id)
            await qimai_store.batch_update_qimai_apps(apps)
            if config.ENABLE_GET_COMMENTS:
                comments = await self.qimai_client.get_app_comments(
                    app_id,
                    config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
                await qimai_store.batch_update_qimai_comments(comments)
            await self._sleep_after_app(app_id)

    async def rank(self) -> None:
        source_keyword_var.set(
            f"rank:{config.QIMAI_RANK_TYPE}:{config.QIMAI_RANK_GENRE}:{config.QIMAI_RANK_DATE or 'latest'}"
        )
        apps = await self.qimai_client.get_rank_apps(
            config.QIMAI_RANK_TYPE,
            config.QIMAI_RANK_DATE,
            config.QIMAI_RANK_GENRE,
            config.QIMAI_RANK_MAX_COUNT,
        )
        for app in apps:
            detail_apps = await self.qimai_client.get_app_detail(app.app_id)
            if detail_apps:
                await qimai_store.batch_update_qimai_apps(
                    [self._merge_rank_detail(app, detail_app) for detail_app in detail_apps]
                )
            else:
                await qimai_store.update_qimai_app(app)
            comments = await self.qimai_client.get_app_comments(
                app.app_id,
                config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
            )
            await qimai_store.batch_update_qimai_comments(comments)
            await self._sleep_after_app(app.app_id)

    @staticmethod
    def _merge_rank_detail(rank_app, detail_app):
        data = rank_app.model_dump()
        for key, value in detail_app.model_dump().items():
            if value and not (key == "app_name" and value in {detail_app.app_id, "七麦数据"} and data.get("app_name")):
                data[key] = value
        return type(rank_app)(**data)

    async def _sleep_after_app(self, app_id: str) -> None:
        interval = max(config.CRAWLER_MAX_SLEEP_SEC, config.QIMAI_CRAWL_INTERVAL_SEC)
        delay = interval + random.uniform(0, 1.5)
        utils.logger.info(f"[QimaiCrawler.rank] app_id={app_id} sleeping {delay:.1f}s to avoid rate limits")
        await asyncio.sleep(delay)

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
            return await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                channel="chrome",
            )
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy, channel="chrome")
        return await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        try:
            self.cdp_manager = CDPBrowserManager()
            return await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )
        except Exception as exc:
            utils.logger.error(f"[QimaiCrawler] CDP launch failed, fallback to standard mode: {exc}")
            return await self.launch_browser(playwright.chromium, playwright_proxy, user_agent, headless)
