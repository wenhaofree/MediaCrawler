# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from media_platform.gzh.core import GzhCrawler
from media_platform.gzh.weread_cli import WereadCliError
from var import reset_gzh_account_stats_seen


STRICT_ARTICLE_URL = (
    "https://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ%3D%3D&mid=2247495310&idx=1"
    "&sn=b7c5d46309bf3c40a574c8843ef141d5&scene=45"
    "&poc_token=HO4VCGujv0cXnLuD7cBau8kvwn9hkNf1epLH_63k"
)


@pytest.mark.asyncio
async def test_creator_crawl_enriches_missing_article_url(monkeypatch):
    class FakeBridge:
        async def book_info(self, _account_id):
            return {}

        async def list_articles(self, _account_id, *, count):
            assert count == 1
            return {
                "articles": [
                    {"reviewId": "review-1", "title": "文章", "createTime": 1000}
                ]
            }

        async def review_single(self, review_id):
            assert review_id == "review-1"
            return {
                "reviewId": review_id,
                "mpInfo": {
                    "originalId": "original-1",
                    "title": "文章",
                    "time": 1000,
                    "doc_url": (
                        "https://mp.weixin.qq.com/mp/wappoc_appmsgcaptcha?"
                        "target_url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%3F"
                        "__biz%3DMzU2MDYzMjgyMQ%3D%3D%26mid%3D2247495310%26idx%3D1"
                        "%26sn%3Db7c5d46309bf3c40a574c8843ef141d5"
                    ),
                },
            }

        async def article_stats(self, _account_id, *, limit):
            assert limit == 1
            return {
                "articles": [
                    {
                        "reviewId": "review-1",
                        "originalId": "original-1",
                        "title": "文章",
                        "publishedAt": 1000,
                        "readCount": 10,
                        "likeCount": 1,
                    }
                ]
            }

    saved_articles = []

    async def fake_save_account(*_args, **_kwargs):
        return None

    async def fake_upsert_article(article):
        saved_articles.append(article)

    monkeypatch.setattr("media_platform.gzh.core.gzh_store.save_account", fake_save_account)
    monkeypatch.setattr("media_platform.gzh.core.gzh_store.upsert_article", fake_upsert_article)
    monkeypatch.setattr("media_platform.gzh.core.config.GZH_REQUEST_INTERVAL_SEC", 0)

    crawler = GzhCrawler.__new__(GzhCrawler)
    crawler.bridge = FakeBridge()
    reset_gzh_account_stats_seen()
    await crawler.crawl_one_account("MP_WXS_3560632821", max_articles=1)

    assert saved_articles[0]["article_url"] == (
        "https://mp.weixin.qq.com/s?__biz=MzU2MDYzMjgyMQ==&mid=2247495310&idx=1&sn=b7c5d46309bf3c40a574c8843ef141d5"
    )


@pytest.mark.asyncio
async def test_creator_crawl_saves_article_when_stats_are_unavailable(monkeypatch):
    class FakeBridge:
        async def book_info(self, _account_id):
            return {}

        async def list_articles(self, _account_id, *, count):
            return {"articles": [{"reviewId": "review-1", "title": "文章", "createTime": 1000}]}

        async def review_single(self, _review_id):
            return {
                "mpInfo": {
                    "originalId": "original-1",
                    "title": "文章",
                    "time": 1000,
                    "doc_url": f"{STRICT_ARTICLE_URL}#rd",
                }
            }

        async def article_stats(self, _account_id, *, limit):
            raise WereadCliError("登录超时")

    saved_articles = []

    async def fake_save_account(*_args, **_kwargs):
        return None

    async def fake_upsert_article(article):
        saved_articles.append(article)

    monkeypatch.setattr("media_platform.gzh.core.gzh_store.save_account", fake_save_account)
    monkeypatch.setattr("media_platform.gzh.core.gzh_store.upsert_article", fake_upsert_article)
    monkeypatch.setattr("media_platform.gzh.core.config.GZH_REQUEST_INTERVAL_SEC", 0)

    crawler = GzhCrawler.__new__(GzhCrawler)
    crawler.bridge = FakeBridge()
    reset_gzh_account_stats_seen()
    result = await crawler.crawl_one_account("MP_WXS_3560632821", max_articles=1)

    assert result["articles_saved"] == 1
    assert result["stats_saved"] is False
    assert saved_articles[0]["article_url"] == STRICT_ARTICLE_URL


@pytest.mark.asyncio
async def test_creator_crawl_drops_non_strict_article_url_without_biz(monkeypatch):
    class FakeBridge:
        async def book_info(self, _account_id):
            return {}

        async def list_articles(self, _account_id, *, count):
            return {
                "articles": [
                    {
                        "reviewId": "review-1",
                        "title": "文章",
                        "createTime": 1000,
                        "mpInfo": {
                            "originalId": "original-1",
                            "title": "文章",
                            "time": 1000,
                            "doc_url": "https://mp.weixin.qq.com/s?id=article-1",
                        },
                    }
                ]
            }

        async def review_single(self, _review_id):
            return {
                "mpInfo": {
                    "originalId": "original-1",
                    "title": "文章",
                    "time": 1000,
                    "doc_url": "https://mp.weixin.qq.com/s/short-only",
                }
            }

        async def article_stats(self, _account_id, *, limit):
            return {"articles": []}

    saved_articles = []

    async def fake_save_account(*_args, **_kwargs):
        return None

    async def fake_upsert_article(article):
        saved_articles.append(article)

    monkeypatch.setattr("media_platform.gzh.core.gzh_store.save_account", fake_save_account)
    monkeypatch.setattr("media_platform.gzh.core.gzh_store.upsert_article", fake_upsert_article)
    monkeypatch.setattr("media_platform.gzh.core.config.GZH_REQUEST_INTERVAL_SEC", 0)

    crawler = GzhCrawler.__new__(GzhCrawler)
    crawler.bridge = FakeBridge()
    reset_gzh_account_stats_seen()
    await crawler.crawl_one_account("MP_WXS_3560632821", max_articles=1)

    assert saved_articles[0]["article_url"] == ""


@pytest.mark.asyncio
async def test_resolve_account_from_article_merges_inspect_and_book_info():
    class FakeBridge:
        async def inspect_article(self, article_url):
            assert article_url == STRICT_ARTICLE_URL
            return {
                "inputUrl": STRICT_ARTICLE_URL,
                "source": "biz+resolve-article",
                "account": {
                    "accountId": "MP_WXS_3560632821",
                    "biz": "MzU2MDYzMjgyMQ==",
                    "bizNumericId": "3560632821",
                    "name": "Python面试官+",
                    "intro": "inspect 简介",
                    "avatar": "https://wx.qlogo.cn/inspect.jpg",
                    "deepLink": "https://weread.qq.com/book-detail?type=1&v=example",
                    "readerLink": "https://weread.qq.com/web/mp/reader/example",
                },
                "article": {
                    "reviewId": "MP_WXS_3560632821_abc",
                    "title": "示例文章",
                    "url": STRICT_ARTICLE_URL,
                    "publishedAt": "2023-11-14T22:13:20.000Z",
                },
                "diagnostics": [],
            }

        async def book_info(self, account_id):
            assert account_id == "MP_WXS_3560632821"
            return {
                "bookId": "MP_WXS_3560632821",
                "title": "Python面试官+",
                "author": "面试官团队",
                "category": "科技互联网",
                "cover": "https://wx.qlogo.cn/book.jpg",
                "intro": "大厂全栈开发",
            }

    crawler = GzhCrawler.__new__(GzhCrawler)
    crawler.bridge = FakeBridge()
    resolved = await crawler.resolve_account_from_article(f"{STRICT_ARTICLE_URL}#rd")

    assert resolved["source"] == "biz+resolve-article"
    assert resolved["account"]["account_id"] == "MP_WXS_3560632821"
    assert resolved["account"]["biz"] == "MzU2MDYzMjgyMQ=="
    assert resolved["account"]["biz_numeric_id"] == "3560632821"
    assert resolved["account"]["nickname"] == "Python面试官+"
    assert resolved["account"]["author"] == "面试官团队"
    assert resolved["account"]["category"] == "科技互联网"
    assert resolved["account"]["reader_link"] == "https://weread.qq.com/web/mp/reader/example"
    assert resolved["article"]["review_id"] == "MP_WXS_3560632821_abc"
    assert resolved["article"]["article_url"] == STRICT_ARTICLE_URL
    assert resolved["article"]["published_at"] == 1700000000


@pytest.mark.asyncio
async def test_crawl_by_article_url_falls_back_when_cli_lacks_inspect_command(monkeypatch):
    class FakeBridge:
        async def inspect_article(self, _article_url):
            raise WereadCliError("error: unknown command 'inspect-article'")

        async def book_info(self, account_id):
            assert account_id == "MP_WXS_3560632821"
            return {
                "bookId": "MP_WXS_3560632821",
                "title": "Python面试官+",
                "author": "作者A",
                "cover": "https://wx.qlogo.cn/book.jpg",
                "intro": "简介A",
            }

    saved = []

    async def fake_save_account(payload, **_kwargs):
        saved.append(payload)

    monkeypatch.setattr("media_platform.gzh.core.gzh_store.save_account", fake_save_account)
    crawler = GzhCrawler.__new__(GzhCrawler)
    crawler.bridge = FakeBridge()
    reset_gzh_account_stats_seen()

    result = await crawler.crawl_by_article_url(STRICT_ARTICLE_URL, fetch_articles=False)
    assert result["account_id"] == "MP_WXS_3560632821"
    assert result["biz"] == "MzU2MDYzMjgyMQ=="
    assert result["nickname"] == "Python面试官+"
    assert result["author"] == "作者A"
    assert saved[0]["account_id"] == "MP_WXS_3560632821"
    assert "biz" not in saved[0]


@pytest.mark.asyncio
async def test_resolve_account_from_short_article_url():
    short_url = "https://mp.weixin.qq.com/s/vYRg2rDw2sK91dltSuWl0Q"

    class FakeBridge:
        async def inspect_article(self, article_url):
            assert article_url == short_url
            return {
                "inputUrl": short_url,
                "source": "weread_mp_review_id",
                "account": {
                    "accountId": "MP_WXS_3271041950",
                    "biz": "MzI3MTA0MTk1MA==",
                    "bizNumericId": "3271041950",
                    "name": "新智元",
                    "avatar": "https://wx.qlogo.cn/xzy.jpg",
                },
                "article": {
                    "title": "刚刚，Anthropic全球最大IPO敲钟 ！",
                    "url": "https://mp.weixin.qq.com/s?__biz=MzI3MTA0MTk1MA==&mid=2652150000&idx=1&sn=1234567890abcdef1234567890abcdef",
                    "reviewId": "MP_WXS_3271041950_1",
                    "publishedAt": 1740618000,
                },
                "diagnostics": [],
            }

        async def book_info(self, account_id):
            assert account_id == "MP_WXS_3271041950"
            return {
                "bookId": "MP_WXS_3271041950",
                "title": "新智元",
                "author": "新智元编辑部",
                "cover": "https://wx.qlogo.cn/xzy_book.jpg",
                "intro": "聚焦人工智能与前沿科技",
            }

    crawler = GzhCrawler.__new__(GzhCrawler)
    crawler.bridge = FakeBridge()
    resolved = await crawler.resolve_account_from_article(f"{short_url}#rd")

    assert resolved["input_url"] == short_url
    assert resolved["source"] == "weread_mp_review_id"
    assert resolved["account"]["account_id"] == "MP_WXS_3271041950"
    assert resolved["account"]["biz"] == "MzI3MTA0MTk1MA=="
    assert resolved["account"]["biz_numeric_id"] == "3271041950"
    assert resolved["account"]["nickname"] == "新智元"
    assert resolved["account"]["author"] == "新智元编辑部"
    assert resolved["article"]["title"] == "刚刚，Anthropic全球最大IPO敲钟 ！"
    assert resolved["article"]["account_id"] == "MP_WXS_3271041950"
    assert resolved["article"]["article_url"] == (
        "https://mp.weixin.qq.com/s?__biz=MzI3MTA0MTk1MA==&mid=2652150000&idx=1&sn=1234567890abcdef1234567890abcdef"
    )

