# -*- coding: utf-8 -*-

from typing import Dict, List, Optional
from urllib.parse import quote

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from base.base_crawler import AbstractApiClient
from model.m_qimai import QimaiApp
from tools import utils

from .help import QimaiExtractor


class QimaiClient(AbstractApiClient):
    def __init__(self, playwright_page: Page, headers: Optional[Dict[str, str]] = None):
        self.playwright_page = playwright_page
        self.headers = headers or {"User-Agent": utils.get_user_agent(), "Cookie": ""}
        self.cookie_urls = ["https://www.qimai.cn", "https://api.qimai.cn"]

    async def request(self, method, url, **kwargs):
        raise NotImplementedError("Qimai uses browser response interception to avoid analysis signing")

    async def update_cookies(self, browser_context: BrowserContext, urls: Optional[list[str]] = None):
        cookie_str, _ = await utils.convert_browser_context_cookies(
            browser_context,
            urls=urls or self.cookie_urls,
        )
        self.headers["Cookie"] = cookie_str

    async def search_apps(self, keyword: str) -> List[QimaiApp]:
        url = f"https://www.qimai.cn/search/index/country/cn/search/{quote(keyword)}"
        return await self._goto_and_extract(url, "/search/index")

    async def get_app_detail(self, app_id: str) -> List[QimaiApp]:
        url = f"https://www.qimai.cn/app/baseinfo/appid/{quote(app_id)}/country/cn"
        return await self._goto_and_extract(url, "/app/baseinfo")

    async def _goto_and_extract(self, url: str, api_path: str) -> List[QimaiApp]:
        try:
            async with self.playwright_page.expect_response(
                lambda response: "api.qimai.cn" in response.url and api_path in response.url,
                timeout=15000,
            ) as response_info:
                await self.playwright_page.goto(url, wait_until="domcontentloaded")
            response = await response_info.value
            payload = await response.json()
        except PlaywrightTimeoutError:
            utils.logger.warning(f"[QimaiClient._goto_and_extract] timeout waiting for {api_path}: {url}")
            return []
        except Exception as exc:
            utils.logger.warning(f"[QimaiClient._goto_and_extract] failed url={url}: {exc}")
            return []
        return QimaiExtractor.extract_apps(payload)
