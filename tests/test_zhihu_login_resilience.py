# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

import pytest

from media_platform.zhihu.client import ZhiHuClient
from media_platform.zhihu.core import ZhihuCrawler
from media_platform.zhihu.login import ZhiHuLogin


class FakeBrowserContextWithUrls:
    def __init__(self, cookies_result):
        self.cookies_result = cookies_result
        self.requested_urls = None

    async def cookies(self, urls=None):
        self.requested_urls = urls
        return self.cookies_result


class FakePage:
    url = "https://www.zhihu.com"


@pytest.mark.asyncio
async def test_zhihu_login_cookie_detects_existing_login():
    browser_context = FakeBrowserContextWithUrls(
        [
            {"name": "z_c0", "value": "login-cookie"},
            {"name": "d_c0", "value": "device-cookie"},
        ]
    )
    login = ZhiHuLogin(
        login_type="qrcode",
        browser_context=browser_context,
        context_page=FakePage(),
    )

    assert await login.is_logged_in_by_cookie() is True
    assert browser_context.requested_urls == [
        "https://www.zhihu.com",
        "https://zhuanlan.zhihu.com",
    ]


@pytest.mark.asyncio
async def test_zhihu_update_cookies_only_reads_zhihu_domains():
    browser_context = FakeBrowserContextWithUrls(
        [
            {"name": "z_c0", "value": "login-cookie"},
            {"name": "d_c0", "value": "device-cookie"},
        ]
    )
    client = ZhiHuClient(
        headers={},
        playwright_page=FakePage(),
        cookie_dict={},
    )

    await client.update_cookies(browser_context)

    assert browser_context.requested_urls == [
        "https://www.zhihu.com",
        "https://zhuanlan.zhihu.com",
    ]
    assert client.default_headers["cookie"] == "z_c0=login-cookie;d_c0=device-cookie"
    assert client.cookie_dict["z_c0"] == "login-cookie"


@pytest.mark.asyncio
async def test_zhihu_create_client_only_reads_zhihu_domain_cookies():
    crawler = ZhihuCrawler()
    crawler.context_page = FakePage()
    crawler.browser_context = FakeBrowserContextWithUrls(
        [
            {"name": "z_c0", "value": "login-cookie"},
            {"name": "d_c0", "value": "device-cookie"},
        ]
    )
    crawler.ip_proxy_pool = None

    client = await crawler.create_zhihu_client(httpx_proxy=None)

    assert crawler.browser_context.requested_urls == [
        "https://www.zhihu.com",
        "https://zhuanlan.zhihu.com",
    ]
    assert client.default_headers["cookie"] == "z_c0=login-cookie;d_c0=device-cookie"
