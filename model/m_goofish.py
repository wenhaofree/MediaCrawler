# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field


class GoofishItem(BaseModel):
    item_id: str = Field(..., description="Item ID")
    title: str = Field(default="", description="Item title")
    desc: str = Field(default="", description="Item description")
    item_url: str = Field(default="", description="Item URL")
    price: str = Field(default="", description="Price text")
    original_price: str = Field(default="", description="Original price text")
    discount_label: str = Field(default="", description="Discount label")
    shipping: str = Field(default="", description="Shipping text")
    area: str = Field(default="", description="Area text")
    image_url: str = Field(default="", description="Main image URL")
    want_count: str = Field(default="", description="Want count")
    browse_count: str = Field(default="", description="Browse count")
    publish_time: str = Field(default="", description="Publish time")
    user_id: str = Field(default="", description="Seller user ID")
    user_nickname: str = Field(default="", description="Seller nickname")
    user_avatar: str = Field(default="", description="Seller avatar URL")
    user_link: str = Field(default="", description="Seller homepage URL")
    creator_hash: str = Field(default="", description="Anonymized seller hash")
    seller_location: str = Field(default="", description="Seller location")
    seller_last_active: str = Field(default="", description="Seller last active text")
    seller_join_time: str = Field(default="", description="Seller join time text")
    seller_sold_count: str = Field(default="", description="Seller sold count text")
    seller_good_rate: str = Field(default="", description="Seller good rate text")
    source_keyword: str = Field(default="", description="Source keyword")
