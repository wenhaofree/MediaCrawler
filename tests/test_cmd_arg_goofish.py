# -*- coding: utf-8 -*-

import config
import pytest
from cmd_arg import parse_cmd


@pytest.mark.asyncio
async def test_goofish_search_cli_sets_platform():
    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "search",
            "--keywords",
            "耳机",
        ]
    )

    assert config.PLATFORM == "goofish"
    assert config.CRAWLER_TYPE == "search"
    assert config.KEYWORDS == "耳机"


@pytest.mark.asyncio
async def test_goofish_detail_cli_does_not_wire_fake_detail_ids(monkeypatch):
    monkeypatch.setattr(config, "GOOFISH_SPECIFIED_ID_LIST", [])

    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "detail",
            "--specified_id",
            "123,456",
        ]
    )

    assert config.GOOFISH_SPECIFIED_ID_LIST == []
