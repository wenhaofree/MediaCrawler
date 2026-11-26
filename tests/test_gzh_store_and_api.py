# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from api.routers import gzh as gzh_api
from media_platform.gzh import weread_cli
from var import reset_gzh_account_stats_seen, should_write_gzh_account_stats


def test_gzh_account_stats_dedupe():
    reset_gzh_account_stats_seen()
    assert should_write_gzh_account_stats("MP_WXS_1") is True
    assert should_write_gzh_account_stats("MP_WXS_1") is False
    assert should_write_gzh_account_stats("MP_WXS_2") is True


def test_resolve_web_cookie_priority(monkeypatch):
    monkeypatch.setattr(weread_cli, "load_dotenv", lambda *a, **k: False, raising=False)
    # Avoid .env override during unit test
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("WEREAD_WEB_COOKIE", "from-weread")
    monkeypatch.setenv("GZH_WEB_COOKIE", "from-gzh-stale")
    monkeypatch.setattr(weread_cli.config, "GZH_WEB_COOKIE", "from-config-stale", raising=False)
    # WEREAD_WEB_COOKIE must win over stale GZH_WEB_COOKIE / config
    assert weread_cli.resolve_web_cookie() == "from-weread"
    assert weread_cli.resolve_web_cookie("from-request") == "from-request"


def test_resolve_web_cookie_reloads_secret_file(monkeypatch, tmp_path):
    import dotenv

    cookie_file = tmp_path / "weread_web_cookie"
    cookie_file.write_text("wr_skey=first", encoding="utf-8")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("WEREAD_WEB_COOKIE_FILE", str(cookie_file))
    monkeypatch.setenv("WEREAD_WEB_COOKIE", "stale-env-cookie")

    assert weread_cli.resolve_web_cookie() == "wr_skey=first"
    cookie_file.write_text("wr_skey=rotated", encoding="utf-8")
    assert weread_cli.resolve_web_cookie() == "wr_skey=rotated"


def test_resolve_web_cookie_strips_quotes(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("WEREAD_WEB_COOKIE", "'wr_skey=abc'")
    monkeypatch.delenv("GZH_WEB_COOKIE", raising=False)
    monkeypatch.setattr(weread_cli.config, "GZH_WEB_COOKIE", "", raising=False)
    assert weread_cli.resolve_web_cookie() == "wr_skey=abc"


@pytest.mark.asyncio
async def test_add_gzh_account_requires_id_or_keyword():
    with pytest.raises(gzh_api.HTTPException) as exc:
        await gzh_api.add_gzh_account(gzh_api.AddAccountRequest())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_gzh_account_saves_account_without_articles(monkeypatch):
    class FakeBridge:
        web_cookie = ""

        def __init__(self, **_kwargs):
            pass

    captured = {}

    class FakeCrawler:
        bridge = None

        async def crawl_one_account(self, account_id, **kwargs):
            captured["account_id"] = account_id
            captured.update(kwargs)
            return {
                "account_id": account_id,
                "nickname": "测试公众号",
                "author": "测试作者",
                "avatar": "https://example.com/avatar.jpg",
                "category": "科技",
                "desc": "测试简介",
                "articles_saved": 0,
                "stats_saved": False,
                "warnings": [],
            }

    monkeypatch.setattr(gzh_api, "WereadOmniBridge", FakeBridge)
    monkeypatch.setattr(gzh_api, "GzhCrawler", FakeCrawler)

    response = await gzh_api.add_gzh_account(
        gzh_api.AddAccountRequest(account_id="2390745668", fetch_articles=False)
    )

    assert response["code"] == 200
    assert response["data"]["account_id"] == "MP_WXS_2390745668"
    assert response["data"]["avatar"] == "https://example.com/avatar.jpg"
    assert captured["account_id"] == "MP_WXS_2390745668"
    assert captured["fetch_articles"] is False


@pytest.mark.asyncio
async def test_inspect_gzh_article_rejects_url_without_biz():
    with pytest.raises(gzh_api.HTTPException) as exc:
        await gzh_api.inspect_gzh_article(
            gzh_api.InspectArticleRequest(article_url="https://mp.weixin.qq.com/s/short-only")
        )
    assert exc.value.status_code == 400
    assert "__biz" in exc.value.detail


@pytest.mark.asyncio
async def test_inspect_gzh_article_returns_account_metadata(monkeypatch):
    sample_url = (
        "https://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ%3D%3D&mid=2247495310&idx=1"
        "&sn=b7c5d46309bf3c40a574c8843ef141d5&scene=45"
        "&poc_token=HO4VCGujv0cXnLuD7cBau8kvwn9hkNf1epLH_63k"
    )

    class FakeBridge:
        web_cookie = ""

        def __init__(self, **_kwargs):
            pass

    class FakeCrawler:
        bridge = None

        async def resolve_account_from_article(self, article_url, *, enrich_book_info=True):
            assert article_url == sample_url
            assert enrich_book_info is True
            return {
                "input_url": article_url,
                "source": "biz+resolve-article",
                "account": {
                    "account_id": "MP_WXS_3560632821",
                    "biz": "MzU2MDYzMjgyMQ==",
                    "biz_numeric_id": "3560632821",
                    "nickname": "Python面试官+",
                    "author": "面试官团队",
                    "avatar": "https://wx.qlogo.cn/avatar.jpg",
                    "category": "科技",
                    "desc": "简介",
                    "deep_link": "https://weread.qq.com/book-detail?type=1&v=example",
                    "reader_link": "https://weread.qq.com/web/mp/reader/example",
                    "entity_subject": None,
                    "entity_subject_available": False,
                },
                "article": {
                    "review_id": "MP_WXS_3560632821_abc",
                    "title": "示例文章",
                    "article_url": article_url,
                    "published_at": 1700000000,
                },
                "diagnostics": [],
            }

    monkeypatch.setattr(gzh_api, "WereadOmniBridge", FakeBridge)
    monkeypatch.setattr(gzh_api, "GzhCrawler", FakeCrawler)

    response = await gzh_api.inspect_gzh_article(
        gzh_api.InspectArticleRequest(article_url=f"{sample_url}#rd")
    )

    assert response["code"] == 200
    assert response["data"]["saved"] is False
    assert response["data"]["account"]["account_id"] == "MP_WXS_3560632821"
    assert response["data"]["account"]["biz"] == "MzU2MDYzMjgyMQ=="
    assert response["data"]["account"]["nickname"] == "Python面试官+"
    assert response["data"]["article"]["review_id"] == "MP_WXS_3560632821_abc"


@pytest.mark.asyncio
async def test_add_gzh_account_by_article_url(monkeypatch):
    sample_url = (
        "https://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ%3D%3D&mid=2247495310&idx=1"
        "&sn=b7c5d46309bf3c40a574c8843ef141d5"
    )

    class FakeBridge:
        web_cookie = ""

        def __init__(self, **_kwargs):
            pass

    captured = {}

    class FakeCrawler:
        bridge = None

        async def crawl_by_article_url(self, article_url, **kwargs):
            captured["article_url"] = article_url
            captured.update(kwargs)
            return {
                "account_id": "MP_WXS_3560632821",
                "biz": "MzU2MDYzMjgyMQ==",
                "biz_numeric_id": "3560632821",
                "nickname": "Python面试官+",
                "author": "面试官团队",
                "avatar": "https://wx.qlogo.cn/avatar.jpg",
                "category": "科技",
                "desc": "简介",
                "deep_link": "",
                "reader_link": "",
                "inspected_article": {"title": "示例文章"},
                "articles_saved": 0,
                "stats_saved": False,
                "warnings": [],
            }

    monkeypatch.setattr(gzh_api, "WereadOmniBridge", FakeBridge)
    monkeypatch.setattr(gzh_api, "GzhCrawler", FakeCrawler)

    response = await gzh_api.add_gzh_account(
        gzh_api.AddAccountRequest(article_url=sample_url, fetch_articles=False)
    )

    assert response["code"] == 200
    assert captured["article_url"] == sample_url
    assert captured["fetch_articles"] is False
    assert response["data"]["account_id"] == "MP_WXS_3560632821"
    assert response["data"]["biz"] == "MzU2MDYzMjgyMQ=="
    assert response["data"]["biz_numeric_id"] == "3560632821"
    assert response["data"]["inspected_article"] == {"title": "示例文章"}


def test_scheduled_task_normalizes_gzh_article_url():
    from api.scheduled_tasks.service import _normalize_creator

    sample_url = (
        "https://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ%3D%3D&mid=2247495310&idx=1"
        "&sn=b7c5d46309bf3c40a574c8843ef141d5&scene=45"
    )
    item = _normalize_creator("gzh", sample_url)
    assert item["normalized_creator_id"] == "MP_WXS_3560632821"

    with pytest.raises(ValueError):
        _normalize_creator("gzh", "https://mp.weixin.qq.com/s/short-only")
