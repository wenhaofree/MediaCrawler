# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import config
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.cookies import (
    cookie_update_hint,
    looks_like_xhs_cookies,
    persist_xhs_cookies,
    resolve_xhs_cookies,
)
from media_platform.xhs.exception import (
    CookieExpiredError,
    DataFetchError,
    IPBlockError,
    PlatformAccessError,
)
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
        description=(
            "自定义 Cookies（可选；未提供时优先热读 Cookie 文件，其次 .env 的 XHS_COOKIES）"
        ),
    )


# Backwards-compatible aliases for existing unit tests.
_looks_like_xhs_cookies = looks_like_xhs_cookies
_resolve_xhs_cookies = resolve_xhs_cookies


def _request_interval_sec() -> float:
    low = float(getattr(config, "XHS_REQUEST_INTERVAL_MIN_SEC", 8.0) or 8.0)
    high = float(getattr(config, "XHS_REQUEST_INTERVAL_MAX_SEC", 15.0) or 15.0)
    if high < low:
        high = low
    return random.uniform(low, high)


async def _wait_between_requests(reason: str) -> None:
    seconds = _request_interval_sec()
    await asyncio.sleep(seconds)
    utils.logger.info("[api.xhs] slept %.1fs %s", seconds, reason)


def _get_xhs_client(cookies_str: Optional[str] = None) -> XiaoHongShuClient:
    cookie_str = resolve_xhs_cookies(cookies_str)
    if not cookie_str or not looks_like_xhs_cookies(cookie_str):
        raise HTTPException(
            status_code=400,
            detail=(
                "未找到有效的小红书 Cookie。"
                "请写入 ./secrets/xhs_cookies（热加载，无需重建容器），"
                "或在 .env 配置 XHS_COOKIES（通常包含 a1 / web_session），"
                "或在请求体传入 cookies。"
            ),
        )
    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
    domain = (
        "https://www.rednote.com"
        if getattr(config, "XHS_INTERNATIONAL", False)
        else "https://www.xiaohongshu.com"
    )
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
        persist_cookies=True,
    )


def _profile_from_creator(creator: Dict[str, Any]) -> Dict[str, Any]:
    return creator.get("basic_info") or creator.get("basicInfo") or creator or {}


def _cookie_expired_http_detail(exc: Optional[BaseException] = None) -> str:
    suffix = f"（{exc}）" if exc else ""
    return f"小红书 Cookie 无效或已过期{suffix}。{cookie_update_hint()}"


def _cookie_source_snapshot(cookie_str: str) -> Dict[str, Any]:
    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
    return {
        "configured": True,
        "looks_like_xhs": looks_like_xhs_cookies(cookie_str),
        "length": len(cookie_str),
        "has_a1": "a1" in cookie_dict,
        "has_web_session": "web_session" in cookie_dict,
        "web_session_prefix": (cookie_dict.get("web_session") or "")[:8] or None,
    }


@router.get("/cookie/inspect")
async def xhs_cookie_inspect():
    """Local-only Cookie resolution check (no outbound call to Xiaohongshu)."""
    try:
        cookie_str = resolve_xhs_cookies()
        if not cookie_str:
            return {
                "code": 400,
                "message": "未解析到 Cookie",
                "data": {
                    "configured": False,
                    "hint": cookie_update_hint(),
                },
            }
        return {
            "code": 200,
            "message": "已解析到 Cookie（未向小红书发请求）",
            "data": {
                **_cookie_source_snapshot(cookie_str),
                "hint": None,
            },
        }
    except Exception as exc:
        utils.logger.exception("[api.xhs] cookie inspect failed: %s", exc)
        return {
            "code": 500,
            "message": f"本地 Cookie 解析异常: {exc}",
            "data": {"configured": False, "hint": cookie_update_hint()},
        }


@router.get("/cookie/status")
async def xhs_cookie_status():
    """Probe whether the currently resolved Cookie is still valid."""
    try:
        cookie_str = resolve_xhs_cookies()
        if not cookie_str or not looks_like_xhs_cookies(cookie_str):
            return {
                "code": 400,
                "message": "未配置有效 Cookie",
                "data": {"valid": False, "hint": cookie_update_hint()},
            }

        client = _get_xhs_client()
        try:
            # Bound the outbound probe so a hung XHS network never wedges the API worker.
            valid = await asyncio.wait_for(client.pong(), timeout=20.0)
        except asyncio.TimeoutError:
            return {
                "code": 504,
                "message": "探测小红书登录态超时（请检查容器出网 / DNS）",
                "data": {
                    "valid": False,
                    "reason": "probe_timeout",
                    **_cookie_source_snapshot(cookie_str),
                },
            }
        except CookieExpiredError as exc:
            return {
                "code": 401,
                "message": _cookie_expired_http_detail(exc),
                "data": {"valid": False, "reason": "cookie_expired"},
            }
        except PlatformAccessError as exc:
            return {
                "code": 403,
                "message": f"小红书访问受限: {exc}",
                "data": {"valid": False, "reason": "access_restricted"},
            }
        except Exception as exc:
            utils.logger.exception("[api.xhs] cookie status probe failed: %s", exc)
            return {
                "code": 502,
                "message": f"Cookie 检测异常: {exc}",
                "data": {"valid": False, "reason": "probe_failed"},
            }

        # Persist any Set-Cookie rotation observed during the probe.
        persist_xhs_cookies(client.headers.get("Cookie", ""))
        return {
            "code": 200,
            "message": "Cookie 有效" if valid else "Cookie 无效或已过期",
            "data": {
                "valid": bool(valid),
                "hint": None if valid else cookie_update_hint(),
                **_cookie_source_snapshot(cookie_str),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        # Never let an unexpected error abort the TCP connection.
        utils.logger.exception("[api.xhs] cookie status crashed: %s", exc)
        return {
            "code": 500,
            "message": f"Cookie 状态接口异常: {exc}",
            "data": {"valid": False, "reason": "internal_error"},
        }


@router.post("/creator/add")
async def add_xhs_creator(req: AddCreatorRequest):
    """
    接收小红书主页链接或 user_id，解析博主资料并入库 xhs_creator；
    可选拉取近期笔记详情写入 xhs_note（及对应 stats）。
    """
    client = _get_xhs_client(req.cookies)
    crawler_type_var.set("api_add")
    reset_xhs_creator_stats_seen()

    try:
        if not await client.pong():
            raise HTTPException(status_code=401, detail=_cookie_expired_http_detail())
    except CookieExpiredError as exc:
        raise HTTPException(status_code=401, detail=_cookie_expired_http_detail(exc)) from exc
    except PlatformAccessError as exc:
        raise HTTPException(
            status_code=403,
            detail=(
                f"小红书访问受限（风控/限流）: {exc}。"
                "请降低采集频率后重试；频繁重试会加速 Cookie 失效。"
            ),
        ) from exc

    try:
        creator_info_parsed = parse_creator_info_from_url(req.url.strip())
        user_id = creator_info_parsed.user_id
        xsec_token = creator_info_parsed.xsec_token or ""
        xsec_source = creator_info_parsed.xsec_source or "pc_search"
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"无法解析小红书账号信息: {exc}") from exc

    await _wait_between_requests("before get_creator_info")

    try:
        creator_res: Dict[str, Any] = await client.get_creator_info(
            user_id=user_id,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
        )
    except CookieExpiredError as exc:
        raise HTTPException(status_code=401, detail=_cookie_expired_http_detail(exc)) from exc
    except (IPBlockError, PlatformAccessError) as exc:
        raise HTTPException(
            status_code=403,
            detail=(
                f"小红书访问受限: {exc}。"
                "请拉长 XHS_REQUEST_INTERVAL_* 并避免短时间重复采集。"
            ),
        ) from exc
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
            await _wait_between_requests("before get_notes_by_creator")
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
                    await _wait_between_requests(f"before note detail {note_id}")
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
                except CookieExpiredError as exc:
                    utils.logger.error(
                        "[api.add_xhs_creator] cookie expired while fetching notes: %s", exc
                    )
                    raise HTTPException(
                        status_code=401, detail=_cookie_expired_http_detail(exc)
                    ) from exc
                except PlatformAccessError as exc:
                    utils.logger.warning(
                        "[api.add_xhs_creator] access restricted on note %s: %s",
                        note_id,
                        exc,
                    )
                    break
                except Exception as exc:
                    utils.logger.warning(
                        f"[api.add_xhs_creator] fetch note {note_id} failed: {exc}"
                    )
        except HTTPException:
            raise
        except Exception as exc:
            utils.logger.warning(f"[api.add_xhs_creator] 拉取笔记入库异常: {exc}")

    # Keep refreshed Set-Cookie (web_session / a1 / websectiga ...) for next request.
    persist_xhs_cookies(client.headers.get("Cookie", ""))

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
