# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

import copy
import urllib.parse
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import config
from media_platform.douyin.client import DouYinClient
from media_platform.douyin.help import parse_creator_info_from_url
from store import douyin as douyin_store
from tools import utils

router = APIRouter(prefix="/douyin", tags=["douyin"])


class AddCreatorRequest(BaseModel):
    url: str = Field(..., description="抖音创作者主页链接或 sec_user_id (支持短链接或完整网页链接)")
    fetch_posts: bool = Field(default=False, description="是否同时拉取并入库其历史作品数据")
    max_posts: int = Field(default=20, ge=1, le=100, description="拉取历史作品的最大数量 (仅当 fetch_posts=True 时生效)")
    cookies: Optional[str] = Field(default=None, description="自定义 Cookies（可选，未提供时默认使用 config/base_config.py 中的 COOKIES）")


def _get_douyin_client(cookies_str: Optional[str] = None) -> DouYinClient:
    cookie_str = cookies_str or config.COOKIES
    if not cookie_str:
        raise HTTPException(
            status_code=400,
            detail="No cookies found. Please configure COOKIES in config/base_config.py or pass them in request.",
        )
    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    headers = {
        "User-Agent": user_agent,
        "Cookie": cookie_str,
        "Host": "www.douyin.com",
        "Referer": "https://www.douyin.com/",
        "Origin": "https://www.douyin.com/",
        "Content-Type": "application/json;charset=UTF-8",
    }
    return DouYinClient(headers=headers, cookie_dict=cookie_dict)


@router.post("/creator/add")
async def add_douyin_creator(req: AddCreatorRequest):
    """
    接收抖音主页链接或 sec_user_id，调用抖音 API 解析博主基本信息，
    并自动入库至 douyin_creator 表（若 fetch_posts=True，还会将作品入库到 douyin_aweme 表）。
    """
    client = _get_douyin_client(req.cookies)

    # 1. 解析短链或主页 URL 提取 sec_user_id
    raw_url = req.url.strip()
    if "v.douyin.com" in raw_url:
        resolved_url = await client.resolve_short_url(raw_url)
        if resolved_url:
            raw_url = resolved_url

    try:
        creator_info_parsed = parse_creator_info_from_url(raw_url)
        sec_user_id = creator_info_parsed.sec_user_id
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无法解析抖音账号信息: {e}")

    # 2. 调用抖音接口获取博主资料
    try:
        creator_res: Dict[str, Any] = await client.get_user_info(sec_user_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"调用抖音博主接口异常: {e}")

    user_data = creator_res.get("user")
    if not user_data:
        raise HTTPException(
            status_code=404,
            detail=f"未找到该博主数据或被风控拦截，返回内容: {creator_res}",
        )

    # 3. 将博主数据入库（保存/更新至 douyin_creator 表）
    try:
        await douyin_store.save_creator(user_id=sec_user_id, creator=creator_res)
    except Exception as e:
        utils.logger.error(f"[api.add_douyin_creator] save_creator error: {e}")
        raise HTTPException(status_code=500, detail=f"保存创作者信息到数据库失败: {e}")

    # 4. 可选：拉取作品并入库
    saved_posts_count = 0
    if req.fetch_posts:
        try:
            posts_res = await client.get_user_aweme_posts(sec_user_id, max_cursor="")
            aweme_list = posts_res.get("aweme_list") or []
            aweme_list = aweme_list[:req.max_posts]
            for aweme_item in aweme_list:
                await douyin_store.update_douyin_aweme(aweme_item)
                saved_posts_count += 1
        except Exception as e:
            utils.logger.warning(f"[api.add_douyin_creator] 拉取作品入库异常: {e}")

    gender_map = {0: "未知", 1: "男", 2: "女"}
    return {
        "code": 200,
        "message": "抖音账号信息解析并入库成功",
        "data": {
            "user_id": sec_user_id,
            "nickname": user_data.get("nickname"),
            "unique_id": user_data.get("unique_id") or user_data.get("short_id"),
            "gender": gender_map.get(user_data.get("gender"), "未知"),
            "signature": user_data.get("signature"),
            "ip_location": user_data.get("ip_location"),
            "following_count": user_data.get("following_count", 0),
            "follower_count": user_data.get("max_follower_count", 0),
            "total_favorited": user_data.get("total_favorited", 0),
            "aweme_count": user_data.get("aweme_count", 0),
            "posts_saved_count": saved_posts_count,
        },
    }

