# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from media_platform.gzh import weread_cli
from media_platform.gzh.weread_cli import (
    biz_from_account_id,
    extract_account_id_from_article_url,
    extract_biz_from_article_url,
    map_book_info_to_account,
    map_mobile_article,
    map_stats_article,
    normalize_account_id,
    normalize_published_at,
    parse_biz_value,
    validate_article_url,
)

SAMPLE_ARTICLE_URL = (
    "https://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ%3D%3D&mid=2247495310&idx=1"
    "&sn=b7c5d46309bf3c40a574c8843ef141d5&scene=45"
    "&poc_token=HO4VCGujv0cXnLuD7cBau8kvwn9hkNf1epLH_63k"
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
    assert normalize_published_at("2023-11-14T22:13:20.000Z") == 1700000000
    assert normalize_published_at(None) is None


def test_parse_biz_and_round_trip():
    parsed = parse_biz_value("MzU2MDYzMjgyMQ%3D%3D")
    assert parsed == {
        "biz": "MzU2MDYzMjgyMQ==",
        "biz_numeric_id": "3560632821",
        "account_id": "MP_WXS_3560632821",
    }
    assert biz_from_account_id("MP_WXS_3560632821") == parsed
    assert parse_biz_value("not-numeric-base64") is None


def test_validate_article_url_strict_rules():
    assert validate_article_url(f"{SAMPLE_ARTICLE_URL}#rd") == SAMPLE_ARTICLE_URL
    assert extract_account_id_from_article_url(SAMPLE_ARTICLE_URL) == "MP_WXS_3560632821"
    assert extract_biz_from_article_url(SAMPLE_ARTICLE_URL)["biz"] == "MzU2MDYzMjgyMQ=="

    for bad_url in [
        "",
        "http://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ==&mid=2247495310&idx=1&sn=abc",
        "https://user:pass@mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ==&mid=2247495310&idx=1&sn=abc",
        "https://mp.weixin.qq.com:8443/s?__biz=MzU2MDYzMjgyMQ==&mid=2247495310&idx=1&sn=abc",
        "https://mp.weixin.qq.com/s/shortlink",
        "https://mp.weixin.qq.com/s?id=article-1",
        "https://mp.weixin.qq.com/s?mid=2247495310&idx=1&sn=b7c5d46309bf3c40a574c8843ef141d5",
        "https://mp.weixin.qq.com/s?__biz=YWJj&mid=2247495310&idx=1&sn=b7c5d46309bf3c40a574c8843ef141d5",
        "https://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ==",
        "https://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ==&mid=2247495310&idx=bad&sn=abc",
    ]:
        with pytest.raises(ValueError):
            validate_article_url(bad_url)


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
                "doc_url": SAMPLE_ARTICLE_URL,
                "pic_url": "https://img",
                "mp_name": "洞见",
                "time": 1794745245000,
            },
        },
    )
    assert mapped["review_id"] == "r1"
    assert mapped["original_id"] == "o1"
    assert mapped["article_url"] == SAMPLE_ARTICLE_URL
    assert "__biz=" in mapped["article_url"]
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


@pytest.mark.asyncio
async def test_inspect_article_validates_url_and_calls_cli(monkeypatch):
    bridge = weread_cli.WereadOmniBridge.__new__(weread_cli.WereadOmniBridge)

    async def fake_run_json(args):
        assert args == ["public-accounts", "inspect-article", SAMPLE_ARTICLE_URL]
        return {
            "inputUrl": SAMPLE_ARTICLE_URL,
            "source": "biz+resolve-article",
            "account": {"accountId": "MP_WXS_3560632821", "name": "Python面试官+"},
            "article": {"reviewId": "r1", "title": "示例"},
        }

    monkeypatch.setattr(bridge, "run_json", fake_run_json)
    result = await bridge.inspect_article(f"{SAMPLE_ARTICLE_URL}#rd")
    assert result["account"]["accountId"] == "MP_WXS_3560632821"

    with pytest.raises(ValueError):
        await bridge.inspect_article("https://mp.weixin.qq.com/s/short-without-biz")
