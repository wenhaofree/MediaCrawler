# -*- coding: utf-8 -*-

import asyncio
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractLogin
from tools import utils


class GooFishLogin(AbstractLogin):
    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = "",
    ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    async def begin(self):
        if config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        elif config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        else:
            raise ValueError("[GooFishLogin.begin] Invalid login type")

    async def login_by_mobile(self):
        raise NotImplementedError("Goofish mobile login is not supported in MVP")

    @retry(stop=stop_after_attempt(180), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        _, cookie_dict = await utils.convert_browser_context_cookies(
            self.browser_context,
            urls=["https://www.goofish.com", "https://h5api.m.goofish.com"],
        )
        return bool(cookie_dict.get("unb") or cookie_dict.get("cookie2") or cookie_dict.get("_m_h5_tk"))

    async def login_by_qrcode(self):
        utils.logger.info("[GooFishLogin.login_by_qrcode] Please finish login in the browser window")
        await self.context_page.goto("https://www.goofish.com", wait_until="domcontentloaded")
        try:
            await self.check_login_state()
        except RetryError:
            utils.logger.info("[GooFishLogin.login_by_qrcode] Login timeout")
            sys.exit()
        await asyncio.sleep(2)

    async def login_by_cookies(self):
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                "name": key,
                "value": value,
                "domain": ".goofish.com",
                "path": "/",
            }])
