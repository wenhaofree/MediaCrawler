# -*- coding: utf-8 -*-

import config
import pytest
from cmd_arg import parse_cmd


@pytest.mark.asyncio
async def test_qimai_search_cli_sets_platform():
    await parse_cmd(
        [
            "--platform",
            "qimai",
            "--type",
            "search",
            "--keywords",
            "微信",
        ]
    )

    assert config.PLATFORM == "qimai"
    assert config.CRAWLER_TYPE == "search"
    assert config.KEYWORDS == "微信"


@pytest.mark.asyncio
async def test_qimai_detail_cli_sets_specified_ids(monkeypatch):
    monkeypatch.setattr(config, "QIMAI_SPECIFIED_ID_LIST", [])

    await parse_cmd(
        [
            "--platform",
            "qimai",
            "--type",
            "detail",
            "--specified_id",
            "414478124,123",
        ]
    )

    assert config.QIMAI_SPECIFIED_ID_LIST == ["414478124", "123"]


@pytest.mark.asyncio
async def test_qimai_rank_cli_sets_rank_options():
    await parse_cmd(
        [
            "--platform",
            "qimai",
            "--type",
            "rank",
            "--qimai_rank_type",
            "free",
            "--qimai_rank_date",
            "2026-09-29",
            "--qimai_rank_genre",
            "6017",
            "--qimai_rank_max_count",
            "0",
            "--qimai_crawl_interval_sec",
            "7",
        ]
    )

    assert config.CRAWLER_TYPE == "rank"
    assert config.QIMAI_RANK_TYPE == "free"
    assert config.QIMAI_RANK_DATE == "2026-09-29"
    assert config.QIMAI_RANK_GENRE == "6017"
    assert config.QIMAI_RANK_MAX_COUNT == 0
    assert config.QIMAI_CRAWL_INTERVAL_SEC == 7
