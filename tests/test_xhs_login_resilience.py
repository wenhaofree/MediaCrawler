# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

import pytest

import config
from media_platform.xhs import login as xhs_login_module
from media_platform.xhs import client as xhs_client_module
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.core import XiaoHongShuCrawler
from media_platform.xhs.exception import DataFetchError
from media_platform.xhs.extractor import XiaoHongShuExtractor
from media_platform.xhs.login import XiaoHongShuLogin


class DummyLoop:
    def run_in_executor(self, executor=None, func=None):
        return None


class FakeBrowserContext:
    async def cookies(self):
        return []


class FakeBrowserContextWithUrls:
    def __init__(self, cookies_result):
        self.cookies_result = cookies_result
        self.requested_urls = None

    async def cookies(self, urls=None):
        self.requested_urls = urls
        return self.cookies_result


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector

    @property
    def first(self):
        return self

    async def wait_for(self, state="visible", timeout=None):
        if not self.page.visible_selectors.get(self.selector, False):
            raise RuntimeError(f"{self.selector} is not visible")

    async def click(self):
        self.page.clicked_selectors.append(self.selector)
        callback = self.page.click_callbacks.get(self.selector)
        if callback:
            callback()


class FakePage:
    def __init__(self, visible_selectors=None, click_callbacks=None):
        self.visible_selectors = visible_selectors or {}
        self.click_callbacks = click_callbacks or {}
        self.clicked_selectors = []
        self.url = "https://www.xiaohongshu.com/explore"

    def locator(self, selector):
        return FakeLocator(self, selector)

    async def is_visible(self, selector, timeout=None):
        return self.visible_selectors.get(selector, False)


async def _noop_sleep(_seconds):
    return None


@pytest.mark.asyncio
async def test_xhs_qrcode_login_uses_existing_qrcode(monkeypatch):
    page = FakePage(visible_selectors={"img.qrcode-img": True})
    login = XiaoHongShuLogin(
        login_type="qrcode",
        browser_context=FakeBrowserContext(),
        context_page=page,
    )

    qrcode_calls = []

    async def fake_find_login_qrcode(_page, selector, timeout_ms=30000):
        qrcode_calls.append((selector, timeout_ms))
        if selector == "img.qrcode-img":
            return "base64-qrcode"
        return ""

    async def fake_check_login_state(_no_logged_in_session):
        return True

    monkeypatch.setattr(xhs_login_module.utils, "find_login_qrcode", fake_find_login_qrcode)
    monkeypatch.setattr(xhs_client_module.asyncio, "sleep", _noop_sleep)
    monkeypatch.setattr(xhs_login_module.asyncio, "get_running_loop", lambda: DummyLoop())
    login.check_login_state = fake_check_login_state  # type: ignore[method-assign]

    await login.login_by_qrcode()

    assert qrcode_calls == [("img.qrcode-img", 5000)]
    assert page.clicked_selectors == []


@pytest.mark.asyncio
async def test_xhs_login_ui_marker_detects_existing_login():
    page = FakePage(
        visible_selectors={
            "xpath=//a[contains(@href, '/user/profile/')]//span[text()='我']": True,
        }
    )
    login = XiaoHongShuLogin(
        login_type="qrcode",
        browser_context=FakeBrowserContext(),
        context_page=page,
    )

    assert await login.is_logged_in_by_ui() is True


@pytest.mark.asyncio
async def test_xhs_qrcode_login_opens_dialog_with_stable_login_button(monkeypatch):
    page = FakePage(
        visible_selectors={
            "button#login-btn": True,
        },
    )

    def show_login_dialog():
        page.visible_selectors["div.login-container"] = True
        page.visible_selectors["img.qrcode-img"] = True

    page.click_callbacks["button#login-btn"] = show_login_dialog

    login = XiaoHongShuLogin(
        login_type="qrcode",
        browser_context=FakeBrowserContext(),
        context_page=page,
    )

    qrcode_calls = []

    async def fake_find_login_qrcode(_page, selector, timeout_ms=30000):
        qrcode_calls.append((selector, timeout_ms))
        if selector == "img.qrcode-img" and page.visible_selectors.get("img.qrcode-img"):
            return "base64-qrcode"
        return ""

    async def fake_check_login_state(_no_logged_in_session):
        return True

    monkeypatch.setattr(xhs_login_module.utils, "find_login_qrcode", fake_find_login_qrcode)
    monkeypatch.setattr(xhs_login_module.asyncio, "sleep", _noop_sleep)
    monkeypatch.setattr(xhs_login_module.asyncio, "get_running_loop", lambda: DummyLoop())
    login.check_login_state = fake_check_login_state  # type: ignore[method-assign]

    await login.login_by_qrcode()

    assert page.clicked_selectors == ["button#login-btn"]
    assert qrcode_calls[0] == ("img.qrcode-img", 5000)
    assert qrcode_calls[-1] == ("img.qrcode-img", 10000)


@pytest.mark.asyncio
async def test_xhs_update_cookies_only_reads_xhs_domains():
    browser_context = FakeBrowserContextWithUrls(
        [
            {"name": "a1", "value": "cookie-a1"},
            {"name": "web_session", "value": "cookie-session"},
        ]
    )
    client = XiaoHongShuClient(
        headers={},
        playwright_page=FakePage(),
        cookie_dict={},
    )

    await client.update_cookies(browser_context)

    assert browser_context.requested_urls == [
        "https://www.xiaohongshu.com",
        "https://edith.xiaohongshu.com",
    ]
    assert client.headers["Cookie"] == "a1=cookie-a1;web_session=cookie-session"
    assert client.cookie_dict["a1"] == "cookie-a1"


@pytest.mark.asyncio
async def test_xhs_create_client_only_reads_xhs_domain_cookies():
    crawler = XiaoHongShuCrawler()
    crawler.context_page = FakePage()
    crawler.browser_context = FakeBrowserContextWithUrls(
        [
            {"name": "a1", "value": "cookie-a1"},
            {"name": "web_session", "value": "cookie-session"},
        ]
    )
    crawler.ip_proxy_pool = None

    client = await crawler.create_xhs_client(httpx_proxy=None)

    assert crawler.browser_context.requested_urls == [
        "https://www.xiaohongshu.com",
        "https://edith.xiaohongshu.com",
    ]
    assert client.headers["Cookie"] == "a1=cookie-a1;web_session=cookie-session"


def test_xhs_extractor_reads_creator_notes_from_html_snapshot():
    extractor = XiaoHongShuExtractor()
    html = """
    <html><body><script>window.__INITIAL_STATE__={
      "user": {
        "notes": [
          [
            {
              "id": "note_1",
              "xsecToken": "token_1",
              "noteCard": {"noteId": "note_1", "displayTitle": "First"}
            },
            {
              "id": "note_2",
              "noteCard": {"noteId": "note_2", "xsecToken": "token_2", "displayTitle": "Second"}
            }
          ],
          []
        ]
      }
    }</script></body></html>
    """

    notes = extractor.extract_creator_notes_from_html(html, xsec_source="pc_search")

    assert notes == [
        {"note_id": "note_1", "xsec_token": "token_1", "xsec_source": "pc_search"},
        {"note_id": "note_2", "xsec_token": "token_2", "xsec_source": "pc_search"},
    ]


@pytest.mark.asyncio
async def test_xhs_get_all_notes_by_creator_falls_back_to_html_snapshot(monkeypatch):
    client = XiaoHongShuClient(
        headers={},
        playwright_page=FakePage(),
        cookie_dict={},
    )

    async def failing_get_notes_by_creator(*args, **kwargs):
        raise DataFetchError('{"code":-1,"success":false}')

    async def html_fallback_notes(*args, **kwargs):
        return {
            "notes": [
                {"note_id": "note_1", "xsec_token": "token_1", "xsec_source": "pc_search"},
                {"note_id": "note_2", "xsec_token": "token_2", "xsec_source": "pc_search"},
            ],
            "has_more": False,
            "cursor": "",
        }

    callback_batches = []

    async def callback(notes):
        callback_batches.append(notes)

    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 15)
    monkeypatch.setattr(xhs_login_module.asyncio, "sleep", _noop_sleep)
    client.get_notes_by_creator = failing_get_notes_by_creator  # type: ignore[method-assign]
    client.get_notes_by_creator_from_html = html_fallback_notes  # type: ignore[method-assign]

    result = await client.get_all_notes_by_creator(
        user_id="creator_1",
        crawl_interval=0,
        callback=callback,
        xsec_token="creator_token",
        xsec_source="pc_search",
    )

    assert [item["note_id"] for item in result] == ["note_1", "note_2"]
    assert len(callback_batches) == 1
