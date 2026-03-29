# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .crawler import PlatformEnum, SaveDataOptionEnum


class ScheduledTaskUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    platform: PlatformEnum
    run_time: str = Field(min_length=5, max_length=5)
    max_pages: int = Field(default=3, gt=0)
    enable_comments: bool = False
    enable_sub_comments: bool = False
    save_option: SaveDataOptionEnum = SaveDataOptionEnum.SQLITE
    status: Literal["active", "paused"] = "active"
    creators: list[str] = Field(default_factory=list, min_length=1)
