# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/login.py
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
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from cache.cache_factory import CacheFactory
from tools import utils


class XiaoHongShuLogin(AbstractLogin):
    LOGIN_DIALOG_SELECTOR = "div.login-container"
    LOGGED_IN_PROFILE_SELECTORS = (
        "xpath=//a[contains(@href, '/user/profile/')]//span[text()='我']",
        "xpath=//a[contains(@href, '/user/profile/') and normalize-space()='我']",
    )
    LOGIN_BUTTON_SELECTORS = (
        "button#login-btn",
        "button.login-btn",
        "xpath=//button[@id='login-btn']",
        "xpath=//button[normalize-space()='登录']",
    )
    QRCODE_SELECTORS = (
        "img.qrcode-img",
        "xpath=//img[contains(@class, 'qrcode-img')]",
        "xpath=//div[contains(@class, 'qrcode')]//img",
    )
    PHONE_LOGIN_SWITCH_SELECTORS = (
        "xpath=//div[contains(@class, 'login-container')]//*[normalize-space()='手机号登录']",
        'xpath=//div[@class="login-container"]//div[@class="other-method"]/div[1]',
    )
    PHONE_INPUT_SELECTOR = "label.phone > input"

    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""
                 ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    async def _wait_for_first_visible_locator(self, selectors, timeout_ms: int = 2000):
        """Return the first visible locator from a selector list."""
        for selector in selectors:
            locator = self.context_page.locator(selector).first
            try:
                await locator.wait_for(state="visible", timeout=timeout_ms)
                return locator
            except Exception:
                continue
        return None

    async def _wait_for_login_dialog(self, timeout_ms: int = 2000) -> bool:
        try:
            await self.context_page.locator(self.LOGIN_DIALOG_SELECTOR).first.wait_for(
                state="visible",
                timeout=timeout_ms,
            )
            return True
        except Exception:
            return False

    async def _open_login_dialog(self) -> bool:
        """Open the login dialog if it is not already visible."""
        if await self._wait_for_login_dialog(timeout_ms=2000):
            return True

        login_button = await self._wait_for_first_visible_locator(
            self.LOGIN_BUTTON_SELECTORS,
            timeout_ms=3000,
        )
        if not login_button:
            utils.logger.error(
                "[XiaoHongShuLogin._open_login_dialog] Login button not found on page: %s",
                self.context_page.url,
            )
            return False

        await login_button.click()
        if await self._wait_for_login_dialog(timeout_ms=5000):
            return True

        utils.logger.error(
            "[XiaoHongShuLogin._open_login_dialog] Login dialog did not appear after clicking login button"
        )
        return False

    async def _find_login_qrcode(self, timeout_ms: int = 5000) -> str:
        """Try multiple selectors to locate the QR code image."""
        for selector in self.QRCODE_SELECTORS:
            base64_qrcode_img = await utils.find_login_qrcode(
                self.context_page,
                selector=selector,
                timeout_ms=timeout_ms,
            )
            if base64_qrcode_img:
                return base64_qrcode_img
        return ""

    async def is_logged_in_by_ui(self) -> bool:
        """Check whether the page already exposes logged-in UI markers."""
        for selector in self.LOGGED_IN_PROFILE_SELECTORS:
            try:
                if await self.context_page.is_visible(selector, timeout=1000):
                    utils.logger.info(
                        "[XiaoHongShuLogin.is_logged_in_by_ui] Login status confirmed by UI element."
                    )
                    return True
            except Exception:
                continue
        return False

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """
        Verify login status using dual-check: UI elements and Cookies.
        """
        # 1. Priority check: Check if the "Me" (Profile) node appears in the sidebar
        if await self.is_logged_in_by_ui():
            return True

        # 2. Alternative: Check for CAPTCHA prompt
        if "请通过验证" in await self.context_page.content():
            utils.logger.info("[XiaoHongShuLogin.check_login_state] CAPTCHA appeared, please verify manually.")

        # 3. Compatibility fallback: Original Cookie-based change detection
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        current_web_session = cookie_dict.get("web_session")
        
        # If web_session has changed, consider the login successful
        if current_web_session and current_web_session != no_logged_in_session:
            utils.logger.info("[XiaoHongShuLogin.check_login_state] Login status confirmed by Cookie (web_session changed).")
            return True

        return False

    async def begin(self):
        """Start login xiaohongshu"""
        utils.logger.info("[XiaoHongShuLogin.begin] Begin login xiaohongshu ...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[XiaoHongShuLogin.begin]I nvalid Login Type Currently only supported qrcode or phone or cookies ...")

    async def login_by_mobile(self):
        """Login xiaohongshu by mobile"""
        utils.logger.info("[XiaoHongShuLogin.login_by_mobile] Begin login xiaohongshu by mobile ...")
        await asyncio.sleep(1)
        if not await self._open_login_dialog():
            utils.logger.info("[XiaoHongShuLogin.login_by_mobile] failed to open login dialog ...")
            sys.exit()

        phone_input = await self._wait_for_first_visible_locator((self.PHONE_INPUT_SELECTOR,), timeout_ms=2000)
        if not phone_input:
            element = await self._wait_for_first_visible_locator(
                self.PHONE_LOGIN_SWITCH_SELECTORS,
                timeout_ms=3000,
            )
            if element:
                await element.click()
            else:
                utils.logger.info(
                    "[XiaoHongShuLogin.login_by_mobile] phone login switch not found, assume phone form is already active ..."
                )

        await asyncio.sleep(1)
        login_container_ele = await self.context_page.wait_for_selector(self.LOGIN_DIALOG_SELECTOR)
        input_ele = await login_container_ele.query_selector("label.phone > input")
        await input_ele.fill(self.login_phone)
        await asyncio.sleep(0.5)

        send_btn_ele = await login_container_ele.query_selector("label.auth-code > span")
        await send_btn_ele.click()  # Click to send verification code
        sms_code_input_ele = await login_container_ele.query_selector("label.auth-code > input")
        submit_btn_ele = await login_container_ele.query_selector("div.input-container > button")
        cache_client = CacheFactory.create_cache(config.CACHE_TYPE_MEMORY)
        max_get_sms_code_time = 60 * 2  # Maximum time to get verification code is 2 minutes
        no_logged_in_session = ""
        while max_get_sms_code_time > 0:
            utils.logger.info(f"[XiaoHongShuLogin.login_by_mobile] get sms code from redis remaining time {max_get_sms_code_time}s ...")
            await asyncio.sleep(1)
            sms_code_key = f"xhs_{self.login_phone}"
            sms_code_value = cache_client.get(sms_code_key)
            if not sms_code_value:
                max_get_sms_code_time -= 1
                continue

            current_cookie = await self.browser_context.cookies()
            _, cookie_dict = utils.convert_cookies(current_cookie)
            no_logged_in_session = cookie_dict.get("web_session")

            await sms_code_input_ele.fill(value=sms_code_value.decode())  # Enter SMS verification code
            await asyncio.sleep(0.5)
            agree_privacy_ele = self.context_page.locator("xpath=//div[@class='agreements']//*[local-name()='svg']")
            await agree_privacy_ele.click()  # Click to agree to privacy policy
            await asyncio.sleep(0.5)

            await submit_btn_ele.click()  # Click login

            # TODO: Should also check if the verification code is correct, as it may be incorrect
            break

        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            utils.logger.info("[XiaoHongShuLogin.login_by_mobile] Login xiaohongshu failed by mobile login method ...")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(f"[XiaoHongShuLogin.login_by_mobile] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_qrcode(self):
        """login xiaohongshu website and keep webdriver login state"""
        utils.logger.info("[XiaoHongShuLogin.login_by_qrcode] Begin login xiaohongshu by qrcode ...")
        # find login qrcode
        base64_qrcode_img = await self._find_login_qrcode(timeout_ms=5000)
        if not base64_qrcode_img:
            utils.logger.info(
                "[XiaoHongShuLogin.login_by_qrcode] qrcode not visible yet, trying to open login dialog ..."
            )
            if not await self._open_login_dialog():
                utils.logger.info("[XiaoHongShuLogin.login_by_qrcode] login failed, could not open login dialog ....")
                sys.exit()

            base64_qrcode_img = await self._find_login_qrcode(timeout_ms=10000)
            if not base64_qrcode_img:
                utils.logger.info(
                    "[XiaoHongShuLogin.login_by_qrcode] login failed, have not found qrcode after opening login dialog ...."
                )
                sys.exit()

        # get not logged session
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("web_session")

        # show login qrcode
        # fix issue #12
        # we need to use partial function to call show_qrcode function and run in executor
        # then current asyncio event loop will not be blocked
        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

        utils.logger.info(f"[XiaoHongShuLogin.login_by_qrcode] waiting for scan code login, remaining time is 120s")
        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            utils.logger.info("[XiaoHongShuLogin.login_by_qrcode] Login xiaohongshu failed by qrcode login method ...")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(f"[XiaoHongShuLogin.login_by_qrcode] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_cookies(self):
        """login xiaohongshu website by cookies"""
        utils.logger.info("[XiaoHongShuLogin.login_by_cookies] Begin login xiaohongshu by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            if key != "web_session":  # Only set web_session cookie attribute
                continue
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".xiaohongshu.com",
                'path': "/"
            }])
