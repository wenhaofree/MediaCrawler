# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field


class QimaiApp(BaseModel):
    app_id: str = Field(..., description="Qimai/App Store app ID")
    app_name: str = Field(default="", description="App name")
    subtitle: str = Field(default="", description="Subtitle")
    publisher: str = Field(default="", description="Publisher/developer")
    category: str = Field(default="", description="Category")
    price: str = Field(default="", description="Price")
    inner_purchase: str = Field(default="", description="In-app purchase text")
    current_rank: str = Field(default="", description="Current rank")
    rank_type: str = Field(default="", description="Rank type")
    rank_date: str = Field(default="", description="Rank date")
    rank_genre: str = Field(default="", description="Rank genre")
    yesterday_downloads: str = Field(default="", description="Yesterday downloads")
    rating_value: str = Field(default="", description="Rating value")
    rating_count: str = Field(default="", description="Rating count")
    icon_url: str = Field(default="", description="Icon URL")
    bundle_id: str = Field(default="", description="Bundle ID")
    release_date: str = Field(default="", description="Release date")
    last_update_date: str = Field(default="", description="Last update date")
    version: str = Field(default="", description="Latest version")
    app_desc: str = Field(default="", description="App description")
    source_keyword: str = Field(default="", description="Source keyword")


class QimaiComment(BaseModel):
    comment_id: str = Field(..., description="Comment ID")
    app_id: str = Field(..., description="Related app ID")
    rating: str = Field(default="", description="Rating")
    title: str = Field(default="", description="Comment title")
    content: str = Field(default="", description="Comment content")
    user_nickname: str = Field(default="", description="Masked user nickname")
    creator_hash: str = Field(default="", description="Anonymous user hash")
    create_time: str = Field(default="", description="Comment time")
    developer_reply: str = Field(default="", description="Developer reply")
    is_deleted: str = Field(default="", description="Deleted marker")
    source_keyword: str = Field(default="", description="Source keyword")
