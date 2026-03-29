# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

from api.schemas import CrawlerStartRequest


def build_crawler_command(config: CrawlerStartRequest) -> list[str]:
    cmd = ["uv", "run", "python", "main.py"]

    cmd.extend(["--platform", config.platform.value])
    cmd.extend(["--lt", config.login_type.value])
    cmd.extend(["--type", config.crawler_type.value])
    cmd.extend(["--save_data_option", config.save_option.value])

    if config.crawler_type.value == "search" and config.keywords:
        cmd.extend(["--keywords", config.keywords])
    elif config.crawler_type.value == "detail" and config.specified_ids:
        cmd.extend(["--specified_id", config.specified_ids])
    elif config.crawler_type.value == "creator" and config.creator_ids:
        cmd.extend(["--creator_id", config.creator_ids])

    if config.start_page != 1:
        cmd.extend(["--start", str(config.start_page)])

    if config.max_pages > 0:
        cmd.extend(["--max_pages", str(config.max_pages)])

    cmd.extend(["--get_comment", "true" if config.enable_comments else "false"])
    cmd.extend(
        ["--get_sub_comment", "true" if config.enable_sub_comments else "false"]
    )

    if config.cookies:
        cmd.extend(["--cookies", config.cookies])

    if config.cdp_attach_only:
        cmd.extend(["--cdp_attach_only", "true"])

    cmd.extend(["--headless", "true" if config.headless else "false"])
    return cmd
