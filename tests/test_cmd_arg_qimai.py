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
