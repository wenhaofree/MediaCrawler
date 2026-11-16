# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from media_platform.gzh.core import GzhCrawler
from media_platform.gzh.weread_cli import WereadCliError
from var import reset_gzh_account_stats_seen


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
                        "target_url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%3Fid%3Darticle-1"
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
    await crawler.crawl_one_account("MP_WXS_1", max_articles=1)

    assert saved_articles[0]["article_url"] == "https://mp.weixin.qq.com/s?id=article-1"


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
                    "doc_url": "https://mp.weixin.qq.com/s?id=article-1",
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
    result = await crawler.crawl_one_account("MP_WXS_1", max_articles=1)

    assert result["articles_saved"] == 1
    assert result["stats_saved"] is False
    assert saved_articles[0]["article_url"] == "https://mp.weixin.qq.com/s?id=article-1"
