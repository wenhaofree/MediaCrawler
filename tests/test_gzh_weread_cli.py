# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from media_platform.gzh import weread_cli
from media_platform.gzh.weread_cli import (
    map_book_info_to_account,
    map_mobile_article,
    map_stats_article,
    normalize_account_id,
    normalize_published_at,
)


def test_normalize_account_id():
    assert normalize_account_id("MP_WXS_2390745668") == "MP_WXS_2390745668"
    assert normalize_account_id("2390745668") == "MP_WXS_2390745668"
    assert normalize_account_id("id=MP_WXS_1") == "MP_WXS_1"
    with pytest.raises(ValueError):
        normalize_account_id("not-an-id")


def test_resolve_cli_path_falls_back_when_configured_missing(monkeypatch, tmp_path):
    from media_platform.gzh import weread_cli

    real = tmp_path / "weread-omni.js"
    real.write_text("#!/usr/bin/env node\n")
    monkeypatch.setattr(weread_cli.config, "WEREAD_OMNI_CLI", "/opt/missing/weread-omni.js", raising=False)
    monkeypatch.setattr(
        weread_cli,
        "_candidate_cli_paths",
        lambda: [str(real)],
    )
    assert weread_cli.resolve_cli_path() == str(real)


def test_normalize_published_at_ms_to_sec():
    assert normalize_published_at(1794745245000) == 1794745245
    assert normalize_published_at(1794745245) == 1794745245
    assert normalize_published_at(None) is None


def test_map_book_info_to_account():
    mapped = map_book_info_to_account(
        "MP_WXS_1",
        {"title": "洞见", "author": "a", "cover": "http://c", "intro": "简介"},
    )
    assert mapped["account_id"] == "MP_WXS_1"
    assert mapped["nickname"] == "洞见"
    assert mapped["avatar"] == "http://c"
    assert mapped["desc"] == "简介"


def test_map_mobile_article():
    mapped = map_mobile_article(
        "MP_WXS_2390745668",
        {
            "reviewId": "r1",
            "mpInfo": {
                "originalId": "o1",
                "title": "标题",
                "content": "摘要",
                "doc_url": "https://mp.weixin.qq.com/s/x",
                "pic_url": "https://img",
                "mp_name": "洞见",
                "time": 1794745245000,
            },
        },
    )
    assert mapped["review_id"] == "r1"
    assert mapped["original_id"] == "o1"
    assert mapped["article_url"].startswith("https://mp.weixin.qq.com")
    assert mapped["published_at"] == 1794745245
    assert mapped["read_count"] is None


def test_map_mobile_article_unwraps_captcha_article_url():
    mapped = map_mobile_article(
        "MP_WXS_3913422171",
        {
            "reviewId": "r1",
            "mpInfo": {
                "title": "标题",
                "doc_url": (
                    "https://mp.weixin.qq.com/mp/wappoc_appmsgcaptcha?"
                    "poc_token=token&target_url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%3F"
                    "__biz%3DMzkxMzQyMjE3MQ%3D%3D%26mid%3D2247528566%26idx%3D5%26sn%3Dfe49495c4914aa8231edf2b6e9df2508"
                ),
            },
        },
    )

    assert mapped["article_url"] == (
        "https://mp.weixin.qq.com/s?__biz=MzkxMzQyMjE3MQ==&mid=2247528566&idx=5&sn=fe49495c4914aa8231edf2b6e9df2508"
    )


def test_map_stats_article():
    mapped = map_stats_article(
        "MP_WXS_2390745668",
        {
            "reviewId": "r1",
            "originalId": "o1",
            "title": "标题",
            "accountName": "洞见",
            "summary": "摘要",
            "readCount": 100000,
            "likeCount": 2691,
            "publishedAt": 1794745245,
        },
    )
    assert mapped["read_count"] == 100000
    assert mapped["like_count"] == 2691
    assert mapped["account_name"] == "洞见"


@pytest.mark.asyncio
async def test_review_single_returns_review_detail(monkeypatch):
    bridge = weread_cli.WereadOmniBridge.__new__(weread_cli.WereadOmniBridge)

    async def fake_run_json(args):
        assert args == ["review", "single", "review-1"]
        return {"review": {"reviewId": "review-1", "mpInfo": {"doc_url": "https://mp.weixin.qq.com/s/x"}}}

    monkeypatch.setattr(bridge, "run_json", fake_run_json)
    detail = await bridge.review_single("review-1")

    assert detail["mpInfo"]["doc_url"] == "https://mp.weixin.qq.com/s/x"
