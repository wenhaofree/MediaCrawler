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
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.exception import DataFetchError, IPBlockError, PlatformAccessError
from media_platform.xhs.help import parse_creator_info_from_url
from store import xhs as xhs_store
from tools import utils
from var import crawler_type_var, reset_xhs_creator_stats_seen

router = APIRouter(prefix="/xhs", tags=["xhs"])


class AddCreatorRequest(BaseModel):
    url: str = Field(
        ...,
        description=(
            "小红书创作者主页链接或 user_id；完整链接建议带 xsec_token，"
            "例如 https://www.xiaohongshu.com/user/profile/xxx?xsec_token=...&xsec_source=pc_search"
        ),
    )
    fetch_posts: bool = Field(default=False, description="是否同时拉取并入库其近期笔记")
    max_posts: int = Field(
        default=20,
        ge=1,
        le=100,
        description="拉取笔记的最大数量（仅当 fetch_posts=True 时生效）",
    )
    cookies: Optional[str] = Field(
        default=None,
        description="自定义 Cookies（可选；未提供时优先使用 .env 的 XHS_COOKIES）",
    )


def _looks_like_xhs_cookies(cookie_str: str) -> bool:
    lower = cookie_str.lower()
    return "a1=" in lower or "web_session=" in lower


def _resolve_xhs_cookies(cookies_str: Optional[str] = None) -> str:
    """
    Priority:
    1) request body cookies
    2) XHS_COOKIES from env / config
    3) config.COOKIES only when it looks like Xiaohongshu cookies
    """
    request_cookies = (cookies_str or "").strip()
    if request_cookies:
        return request_cookies

    xhs_cookies = (
        getattr(config, "XHS_COOKIES", None) or os.getenv("XHS_COOKIES") or ""
    ).strip()
    if xhs_cookies:
        return xhs_cookies

    fallback = (config.COOKIES or "").strip()
    if fallback and _looks_like_xhs_cookies(fallback):
        return fallback
    return ""


def _get_xhs_client(cookies_str: Optional[str] = None) -> XiaoHongShuClient:
    cookie_str = _resolve_xhs_cookies(cookies_str)
    if not cookie_str or not _looks_like_xhs_cookies(cookie_str):
        raise HTTPException(
            status_code=400,
            detail=(
                "未找到有效的小红书 Cookie。请在 .env 配置 XHS_COOKIES"
                "（通常包含 a1 / web_session），或在请求体传入 cookies。"
            ),
        )
    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
    domain = "https://www.rednote.com" if getattr(config, "XHS_INTERNATIONAL", False) else "https://www.xiaohongshu.com"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "no-cache",
        "content-type": "application/json;charset=UTF-8",
        "origin": domain,
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": f"{domain}/",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        ),
        "Cookie": cookie_str,
    }
    return XiaoHongShuClient(
        headers=headers,
        playwright_page=None,
        cookie_dict=cookie_dict,
    )


def _profile_from_creator(creator: Dict[str, Any]) -> Dict[str, Any]:
    return creator.get("basic_info") or creator.get("basicInfo") or creator or {}


@router.post("/creator/add")
async def add_xhs_creator(req: AddCreatorRequest):
    """
    接收小红书主页链接或 user_id，解析博主资料并入库 xhs_creator；
    可选拉取近期笔记详情写入 xhs_note（及对应 stats）。
    """
    client = _get_xhs_client(req.cookies)
    crawler_type_var.set("api_add")
    reset_xhs_creator_stats_seen()

    if not await client.pong():
        raise HTTPException(
            status_code=401,
            detail="小红书 Cookie 无效或已过期，请更新 .env 中的 XHS_COOKIES 后重试",
        )

    try:
        creator_info_parsed = parse_creator_info_from_url(req.url.strip())
        user_id = creator_info_parsed.user_id
        xsec_token = creator_info_parsed.xsec_token or ""
        xsec_source = creator_info_parsed.xsec_source or "pc_search"
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"无法解析小红书账号信息: {exc}") from exc

    try:
        creator_res: Dict[str, Any] = await client.get_creator_info(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
        )
    except (IPBlockError, PlatformAccessError) as exc:
        raise HTTPException(status_code=403, detail=f"小红书访问受限: {exc}") from exc
    except DataFetchError as exc:
        raise HTTPException(status_code=502, detail=f"调用小红书博主接口失败: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"调用小红书博主接口异常: {exc}") from exc

    if not creator_res:
        raise HTTPException(
            status_code=404,
            detail="未找到该博主数据，或主页 HTML 解析失败（建议使用带 xsec_token 的完整主页链接）",
        )

    try:
        await xhs_store.save_creator(user_id, creator=creator_res)
    except Exception as exc:
        utils.logger.error(f"[api.add_xhs_creator] save_creator error: {exc}")
        raise HTTPException(status_code=500, detail=f"保存创作者信息到数据库失败: {exc}") from exc

    saved_posts_count = 0
    if req.fetch_posts:
        try:
            notes_res = await client.get_notes_by_creator(
                creator=user_id,
                cursor="",
                page_size=min(req.max_posts, 30),
                xsec_token=xsec_token,
                xsec_source=xsec_source or "pc_feed",
            )
            notes = (notes_res or {}).get("notes") or []
            for note_item in notes[: req.max_posts]:
                note_id = note_item.get("note_id")
                if not note_id:
                    continue
                note_token = note_item.get("xsec_token") or xsec_token
                note_source = note_item.get("xsec_source") or xsec_source or "pc_feed"
                try:
                    note_detail = await client.get_note_by_id(
                        note_id=note_id,
                        xsec_source=note_source,
                        xsec_token=note_token,
                    )
                    if note_detail:
                        note_detail.update(
                            {"xsec_token": note_token, "xsec_source": note_source}
                        )
                        await xhs_store.update_xhs_note(note_detail)
                        saved_posts_count += 1
                except Exception as exc:
                    utils.logger.warning(
                        f"[api.add_xhs_creator] fetch note {note_id} failed: {exc}"
                    )
                await asyncio.sleep(getattr(config, "CRAWLER_MAX_SLEEP_SEC", 1))
        except Exception as exc:
            utils.logger.warning(f"[api.add_xhs_creator] 拉取笔记入库异常: {exc}")

    profile = _profile_from_creator(creator_res)
    interaction_counts = {
        str(item.get("type")): item.get("count", "")
        for item in (creator_res.get("interactions") or profile.get("interactions") or [])
        if isinstance(item, dict)
    }
    avatar = profile.get("image") or profile.get("avatar") or ""
    if isinstance(avatar, list):
        avatar = avatar[0] if avatar else ""

    return {
        "code": 200,
        "message": "小红书账号信息解析并入库成功",
        "data": {
            "user_id": user_id,
            "nickname": profile.get("nickname"),
            "avatar": avatar,
            "desc": profile.get("desc"),
            "gender": profile.get("gender"),
            "ip_location": profile.get("ip_location"),
            "follows": interaction_counts.get("follows", profile.get("follows")),
            "fans": interaction_counts.get("fans", profile.get("fans")),
            "interaction": interaction_counts.get("interaction", profile.get("interaction")),
            "xsec_token": xsec_token,
            "xsec_source": xsec_source,
            "profile_url": (
                f"https://www.xiaohongshu.com/user/profile/{user_id}"
                + (f"?xsec_token={xsec_token}&xsec_source={xsec_source}" if xsec_token else "")
            ),
            "posts_saved_count": saved_posts_count,
        },
    }
