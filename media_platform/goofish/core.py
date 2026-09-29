# -*- coding: utf-8 -*-

import asyncio
import os
from typing import Dict, Optional

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import goofish as goofish_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import GooFishClient
from .login import GooFishLogin


class GooFishCrawler(AbstractCrawler):
    context_page: Page
    goofish_client: GooFishClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.goofish.com"
        self.cookie_urls = [self.index_url, "https://h5api.m.goofish.com"]
        self.user_agent = utils.get_user_agent()
        self.cdp_manager = None

    async def start(self) -> None:
        playwright_proxy_format, _ = None, None
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
            self.goofish_client = GooFishClient(
                playwright_page=self.context_page,
                headers={"User-Agent": self.user_agent, "Cookie": ""},
            )
            if config.LOGIN_TYPE == "cookie" and config.COOKIES:
                await GooFishLogin(
                    login_type=config.LOGIN_TYPE,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                ).begin()
            await self.goofish_client.update_cookies(self.browser_context, self.cookie_urls)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            else:
                utils.logger.info("[GooFishCrawler.start] Goofish MVP only supports search")

            utils.logger.info("[GooFishCrawler.start] Goofish crawler finished")

    async def search(self) -> None:
        page_size = 30
        if config.CRAWLER_MAX_NOTES_COUNT < page_size:
            config.CRAWLER_MAX_NOTES_COUNT = page_size
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue
            source_keyword_var.set(keyword)
            page = 1
            while (page - start_page + 1) * page_size <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    page += 1
                    continue
                utils.logger.info(f"[GooFishCrawler.search] keyword={keyword}, page={page}")
                items = await self.goofish_client.search_items(keyword, page, page_size)
                if not items:
                    break
                await goofish_store.batch_update_goofish_items(items)
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                page += 1

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
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )
            utils.logger.info(f"[GooFishCrawler] CDP browser info: {await self.cdp_manager.get_browser_info()}")
            return browser_context
        except Exception as e:
            utils.logger.error(f"[GooFishCrawler] CDP launch failed, fallback to standard mode: {e}")
            return await self.launch_browser(playwright.chromium, playwright_proxy, user_agent, headless)

    async def close(self):
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
