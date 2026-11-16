# -*- coding: utf-8 -*-
from __future__ import annotations

from store.gzh._store_impl import _prefer_review_id, _norm_id


def test_prefer_review_id_prefers_stats_style():
    mobile = "MP_WXS_2390745668_89nTFvKfcn3aq4fAHafaGQ"
    stats = (
        "MP_WXS_2390745668_WR1EYR3TbEcM8Pp3B0BYB9l35yVBUA9foEtp4iA5Be4TL1x8Fn11A5AoDAP6CMJBqiGesD230Zd"
    )
    assert _prefer_review_id(mobile, stats) == stats
    assert _prefer_review_id(stats, mobile) == stats
    assert _prefer_review_id("", stats) == stats
    assert _norm_id("  abc  ") == "abc"


def test_map_stats_and_mobile_share_title_for_merge():
    from media_platform.gzh.weread_cli import map_mobile_article, map_stats_article

    mobile = map_mobile_article(
        "MP_WXS_1",
        {
            "reviewId": "MP_WXS_1_abc",
            "mpInfo": {"title": "同一标题", "time": 1000, "content": "m"},
        },
    )
    stats = map_stats_article(
        "MP_WXS_1",
        {
            "reviewId": "MP_WXS_1_WRxxx",
            "originalId": "WRxxx",
            "title": "同一标题",
            "publishedAt": 1000,
            "readCount": 9,
        },
    )
    assert mobile["title"] == stats["title"]
    assert mobile["review_id"] != stats["review_id"]
    assert stats["original_id"] == "WRxxx"


def test_merge_article_sources_combines_cover_and_read():
    from media_platform.gzh.weread_cli import merge_article_sources

    mobile = [
        {
            "account_id": "MP_WXS_1",
            "review_id": "MP_WXS_1_abc",
            "original_id": "",
            "title": "同一标题",
            "published_at": 1000,
            "cover_url": "https://cover/a.jpg",
            "article_url": "https://mp/a",
            "read_count": None,
            "like_count": None,
        }
    ]
    stats = [
        {
            "account_id": "MP_WXS_1",
            "review_id": "MP_WXS_1_WRxxx",
            "original_id": "WRxxx",
            "title": "同一标题",
            "published_at": 1000,
            "cover_url": "",
            "article_url": "",
            "read_count": 12345,
            "like_count": 10,
        }
    ]
    merged = merge_article_sources(mobile, stats)
    assert len(merged) == 1
    row = merged[0]
    assert row["cover_url"] == "https://cover/a.jpg"
    assert row["read_count"] == 12345
    assert row["like_count"] == 10
    assert "WR" in row["review_id"]
    assert row["original_id"] == "WRxxx"
