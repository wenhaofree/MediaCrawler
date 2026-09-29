# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field


class GoofishItem(BaseModel):
    item_id: str = Field(..., description="Item ID")
    title: str = Field(default="", description="Item title")
    desc: str = Field(default="", description="Item description")
    item_url: str = Field(default="", description="Item URL")
    price: str = Field(default="", description="Price text")
    area: str = Field(default="", description="Area text")
    image_url: str = Field(default="", description="Main image URL")
    want_count: str = Field(default="", description="Want count")
    browse_count: str = Field(default="", description="Browse count")
    publish_time: str = Field(default="", description="Publish time")
    user_nickname: str = Field(default="", description="Masked seller nickname")
    creator_hash: str = Field(default="", description="Anonymized seller hash")
    source_keyword: str = Field(default="", description="Source keyword")
