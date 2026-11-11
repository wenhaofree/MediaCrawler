# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.

import asyncio
import pytest

import config
from media_platform.douyin.client import DouYinClient
from media_platform.douyin.core import DouYinCrawler
from media_platform.douyin.help import get_a_bogus, generate_ms_token, get_web_id
from tools.sign_client import SignServiceClient


@pytest.mark.asyncio
async def test_generate_tokens_and_ids():
    token = generate_ms_token(107)
    assert len(token) == 107
    assert isinstance(token, str)

    web_id = get_web_id()
    assert len(web_id) > 10
    assert web_id.isdigit()


@pytest.mark.asyncio
async def test_get_a_bogus_fallback_when_sign_service_offline(monkeypatch):
    # Set sign service to a non-existent port
    monkeypatch.setattr(config, "SIGN_SERVICE_URL", "http://127.0.0.1:59999")
    monkeypatch.setattr(config, "ENABLE_SIGN_SERVICE", True)
    SignServiceClient._last_failure_time = 0.0

    # Must smoothly fallback to local execjs without error
    a_bogus = await get_a_bogus(
        url="/aweme/v1/web/aweme/post/",
        params="device_platform=webapp&aid=6383",
        post_data={},
        user_agent="Mozilla/5.0",
        page=None,
    )
    assert a_bogus
    assert isinstance(a_bogus, str)
    assert a_bogus.endswith("=")


@pytest.mark.asyncio
async def test_douyin_client_pure_api_req_params():
    client = DouYinClient(
        headers={"User-Agent": "Mozilla/5.0"},
        playwright_page=None,
        cookie_dict={"LOGIN_STATUS": "1", "webid": "1234567890123456789"},
    )

    params = {"sec_user_id": "test_sec_uid", "count": 18}
    await client._DouYinClient__process_req_params("/aweme/v1/web/aweme/post/", params)

    assert "a_bogus" in params
    assert len(params["a_bogus"]) > 10
    assert params["webid"] == "1234567890123456789"
    assert "msToken" in params
    assert len(params["msToken"]) > 0
    assert params["device_platform"] == "webapp"


@pytest.mark.asyncio
async def test_douyin_client_pure_api_pong():
    # When cookie_dict has LOGIN_STATUS == 1
    client = DouYinClient(
        headers={},
        playwright_page=None,
        cookie_dict={"LOGIN_STATUS": "1"},
    )
    assert await client.pong(None) is True

    # When not logged in
    client_unlogged = DouYinClient(
        headers={},
        playwright_page=None,
        cookie_dict={},
    )
    assert await client_unlogged.pong(None) is False


@pytest.mark.asyncio
async def test_douyin_crawler_pure_api_session_init(monkeypatch):
    monkeypatch.setattr(config, "COOKIES", "my_custom_cookie=hello_val; LOGIN_STATUS=1")
    crawler = DouYinCrawler()

    cookie_str, cookie_dict = await crawler.init_pure_api_session()

    assert "my_custom_cookie" in cookie_dict
    assert cookie_dict["my_custom_cookie"] == "hello_val"
    assert "webid" in cookie_dict
    assert "msToken" in cookie_dict
    assert "my_custom_cookie=hello_val" in cookie_str


@pytest.mark.asyncio
async def test_node_sign_service_integration(monkeypatch):
    import subprocess
    import sys
    import os

    # Start Node sign service on a test port
    test_port = "9099"
    env = os.environ.copy()
    env["PORT"] = test_port
    proc = subprocess.Popen(
        ["node", "services/sign_srv/server.js"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Give it a moment to boot
        await asyncio.sleep(1.0)
        monkeypatch.setattr(config, "SIGN_SERVICE_URL", f"http://127.0.0.1:{test_port}")
        monkeypatch.setattr(config, "ENABLE_SIGN_SERVICE", True)
        SignServiceClient._last_failure_time = 0.0

        sign = await SignServiceClient.get_douyin_a_bogus(
            url="/aweme/v1/web/aweme/post/",
            params="device_platform=webapp&aid=6383",
            user_agent="Mozilla/5.0",
        )
        assert sign is not None
        assert isinstance(sign, str)
        assert len(sign) > 20
        assert sign.endswith("=")
    finally:
        proc.terminate()
        proc.wait(timeout=3)
