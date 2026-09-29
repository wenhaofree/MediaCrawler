# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field


class QimaiApp(BaseModel):
    app_id: str = Field(..., description="Qimai/App Store app ID")
    app_name: str = Field(default="", description="App name")
    subtitle: str = Field(default="", description="Subtitle")
    publisher: str = Field(default="", description="Publisher/developer")
    category: str = Field(default="", description="Category")
    current_rank: str = Field(default="", description="Current rank")
    rating_value: str = Field(default="", description="Rating value")
    rating_count: str = Field(default="", description="Rating count")
    icon_url: str = Field(default="", description="Icon URL")
    bundle_id: str = Field(default="", description="Bundle ID")
    release_date: str = Field(default="", description="Release date")
    last_update_date: str = Field(default="", description="Last update date")
    version: str = Field(default="", description="Latest version")
    app_desc: str = Field(default="", description="App description")
    source_keyword: str = Field(default="", description="Source keyword")
