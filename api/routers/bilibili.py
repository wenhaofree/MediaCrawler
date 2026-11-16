# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import config
from media_platform.bilibili.client import BilibiliClient
from media_platform.bilibili.exception import DataFetchError
from media_platform.bilibili.help import parse_creator_info_from_url
from store import bilibili as bilibili_store
from tools import utils
from var import crawler_type_var, reset_bili_creator_stats_seen

router = APIRouter(prefix="/bilibili", tags=["bilibili"])


class AddCreatorRequest(BaseModel):
    url: str = Field(
        ...,
        description="B站 UP 主空间链接或 UID，例如 https://space.bilibili.com/20813884 或 20813884",
    )
    fetch_posts: bool = Field(default=False, description="是否同时拉取并入库其近期作品")
    max_posts: int = Field(
        default=20,
        ge=1,
        le=100,
        description="拉取作品的最大数量（仅当 fetch_posts=True 时生效）",
    )
    cookies: Optional[str] = Field(
        default=None,
        description="自定义 Cookies（可选；未提供时优先使用 .env 的 BILI_COOKIES）",
    )


def _looks_like_bili_cookies(cookie_str: str) -> bool:
    upper = cookie_str.upper()
    return "SESSDATA=" in upper or "DEDEUSERID=" in upper


def _resolve_bili_cookies(cookies_str: Optional[str] = None) -> str:
    """
    Priority:
    1) request body cookies
    2) BILI_COOKIES from env / config
    3) config.COOKIES only when it looks like Bilibili login cookies
       (avoid mistakenly sending Douyin cookies and getting 账号未登录)
    """
    request_cookies = (cookies_str or "").strip()
    if request_cookies:
        return request_cookies

    bili_cookies = (
        getattr(config, "BILI_COOKIES", None) or os.getenv("BILI_COOKIES") or ""
    ).strip()
    if bili_cookies:
        return bili_cookies

    fallback = (config.COOKIES or "").strip()
    if fallback and _looks_like_bili_cookies(fallback):
        return fallback
    return ""


def _get_bilibili_client(cookies_str: Optional[str] = None) -> BilibiliClient:
    cookie_str = _resolve_bili_cookies(cookies_str)
    if not cookie_str or not _looks_like_bili_cookies(cookie_str):
        raise HTTPException(
            status_code=400,
            detail=(
                "未找到有效的 B站 Cookie。请在 .env 配置 BILI_COOKIES"
                "（至少包含 SESSDATA），或在请求体传入 cookies。"
            ),
        )
    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    headers = {
        "User-Agent": user_agent,
        "Referer": "https://space.bilibili.com",
        "Origin": "https://www.bilibili.com",
        "Cookie": cookie_str,
    }
    return BilibiliClient(
        headers=headers,
        playwright_page=None,
        cookie_dict=cookie_dict,
    )


@router.post("/creator/add")
async def add_bilibili_creator(req: AddCreatorRequest):
    """
    接收 B站空间链接或 UID，解析 UP 主资料并入库 bilibili_up_info；
    可选拉取近期作品详情写入 bilibili_video（及对应 stats）。
    """
    client = _get_bilibili_client(req.cookies)
    crawler_type_var.set("api_add")
    reset_bili_creator_stats_seen()

    try:
        creator_info_parsed = parse_creator_info_from_url(req.url.strip())
        creator_id = int(creator_info_parsed.creator_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"无法解析 B站账号信息: {exc}") from exc

    try:
        creator_res: Dict[str, Any] = await client.get_creator_info(creator_id)
    except DataFetchError as exc:
        raise HTTPException(status_code=502, detail=f"调用 B站博主接口失败: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"调用 B站博主接口异常: {exc}") from exc

    if not creator_res or not (creator_res.get("mid") or creator_res.get("name")):
        raise HTTPException(
            status_code=404,
            detail=f"未找到该 UP 主数据或被风控拦截，返回内容: {creator_res}",
        )

    relation_stat: Dict[str, Any] = {}
    up_stat: Dict[str, Any] = {}
    try:
        relation_stat = await client.get_creator_relation_stat(creator_id) or {}
    except Exception as exc:
        utils.logger.warning(f"[api.add_bilibili_creator] relation/stat failed: {exc}")
    try:
        up_stat = await client.get_creator_up_stat(creator_id) or {}
    except Exception as exc:
        utils.logger.warning(f"[api.add_bilibili_creator] upstat failed: {exc}")

    try:
        await bilibili_store.save_creator(
            user_id=creator_id,
            creator_info=creator_res,
            relation_stat=relation_stat,
            up_stat=up_stat,
        )
    except Exception as exc:
        utils.logger.error(f"[api.add_bilibili_creator] save_creator error: {exc}")
        raise HTTPException(status_code=500, detail=f"保存 UP 主信息到数据库失败: {exc}") from exc

    saved_posts_count = 0
    if req.fetch_posts:
        try:
            posts_res = await client.get_creator_videos(str(creator_id), pn=1, ps=min(req.max_posts, 30))
            vlist = ((posts_res or {}).get("list") or {}).get("vlist") or []
            bvids = [item.get("bvid") for item in vlist if item.get("bvid")][: req.max_posts]
            for bvid in bvids:
                try:
                    detail = await client.get_video_info(bvid=bvid)
                    if detail:
                        await bilibili_store.update_bilibili_video(detail)
                        saved_posts_count += 1
                except Exception as exc:
                    utils.logger.warning(
                        f"[api.add_bilibili_creator] fetch video {bvid} failed: {exc}"
                    )
                await asyncio.sleep(getattr(config, "CRAWLER_MAX_SLEEP_SEC", 1))
        except Exception as exc:
            utils.logger.warning(f"[api.add_bilibili_creator] 拉取作品入库异常: {exc}")

    likes = up_stat.get("likes")
    if likes is None and isinstance(up_stat.get("archive"), dict):
        likes = up_stat["archive"].get("likes")

    return {
        "code": 200,
        "message": "B站账号信息解析并入库成功",
        "data": {
            "user_id": str(creator_id),
            "nickname": creator_res.get("name"),
            "sex": creator_res.get("sex"),
            "sign": creator_res.get("sign"),
            "avatar": creator_res.get("face"),
            "level": (creator_res.get("level_info") or {}).get("current_level", creator_res.get("level")),
            "follower_count": relation_stat.get("follower"),
            "following_count": relation_stat.get("following"),
            "total_liked": likes,
            "space_url": f"https://space.bilibili.com/{creator_id}",
            "posts_saved_count": saved_posts_count,
        },
    }
