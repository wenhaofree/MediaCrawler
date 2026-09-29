# -*- coding: utf-8 -*-

from playwright.async_api import BrowserContext, Page

import config
from base.base_crawler import AbstractLogin
from tools import utils


class QimaiLogin(AbstractLogin):
    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        cookie_str: str = "",
    ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.cookie_str = cookie_str

    async def begin(self):
        if config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            utils.logger.info("[QimaiLogin.begin] Qimai MVP uses current browser session; login skipped")

    async def login_by_qrcode(self):
        await self.begin()

    async def login_by_mobile(self):
        await self.begin()

    async def login_by_cookies(self):
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                "name": key,
                "value": value,
                "domain": ".qimai.cn",
                "path": "/",
            }])
