# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""Database-backed runtime config & platform cookie management."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from dotenv import dotenv_values
from sqlalchemy import select

import config
from database.db_session import get_async_engine, get_session
from database.models import AppConfig, Base, DouyinCreator, GzhAccount
from tools import utils

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
DB_SAVE_OPTIONS = {"postgres", "db", "mysql", "sqlite"}


@dataclass(frozen=True)
class PlatformCookieSpec:
    platform: str
    config_key: str
    label: str
    env_keys: Tuple[str, ...]
    secret_file_env: str = ""
    default_secret_file: str = ""
    hint: str = ""


PLATFORM_COOKIE_SPECS: Dict[str, PlatformCookieSpec] = {
    "dy": PlatformCookieSpec(
        platform="dy",
        config_key="dy_cookies",
        label="抖音 (Douyin)",
        env_keys=("DY_COOKIES",),
        hint="从 www.douyin.com 复制完整请求头 Cookie（需含 sessionid / ttwid 等字段）。",
    ),
    "bili": PlatformCookieSpec(
        platform="bili",
        config_key="bili_cookies",
        label="B站 (Bilibili)",
        env_keys=("BILI_COOKIES",),
        hint="从 www.bilibili.com 复制 Cookie（需含 SESSDATA、bili_jct、DedeUserID）。",
    ),
    "xhs": PlatformCookieSpec(
        platform="xhs",
        config_key="xhs_cookies",
        label="小红书 (Xiaohongshu)",
        env_keys=("XHS_COOKIES",),
        secret_file_env="XHS_COOKIES_FILE",
        default_secret_file="/run/secrets/xhs_cookies",
        hint="推荐使用独立小号从 www.xiaohongshu.com 复制 Cookie（需含 a1、web_session）。",
    ),
    "gzh": PlatformCookieSpec(
        platform="gzh",
        config_key="weread_web_cookie",
        label="公众号 / 微信读书 Web Cookie",
        env_keys=("WEREAD_WEB_COOKIE", "GZH_WEB_COOKIE"),
        secret_file_env="WEREAD_WEB_COOKIE_FILE",
        default_secret_file="/run/secrets/weread_web_cookie",
        hint="从 weread.qq.com 复制网页版 Cookie（需含 wr_vid、wr_skey；移动端扫码态仍存在 /root/.config/weread）。",
    ),
}


def _now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds")


def _strip_cookie(value: Optional[str]) -> str:
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    return text


def mask_cookie(value: Optional[str]) -> str:
    raw = _strip_cookie(value)
    if not raw:
        return ""
    if len(raw) <= 16:
        return "*" * len(raw)
    return f"{raw[:8]}...{raw[-6:]}"


def _active_db_option() -> Optional[str]:
    save_opt = (
        os.getenv("SAVE_DATA_OPTION", "").strip()
        or getattr(config, "SAVE_DATA_OPTION", "")
        or ""
    ).strip().lower()
    if save_opt in DB_SAVE_OPTIONS:
        return save_opt
    if os.getenv("DATABASE_URL", "").strip() or os.getenv("POSTGRES_DB_HOST", "").strip():
        return "postgres"
    return None


async def ensure_app_config_table() -> bool:
    db_opt = _active_db_option()
    if not db_opt:
        return False
    prev = getattr(config, "SAVE_DATA_OPTION", None)
    try:
        config.SAVE_DATA_OPTION = db_opt
        engine = get_async_engine(db_opt)
        if not engine:
            return False
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn, tables=[AppConfig.__table__]
                )
            )
        return True
    except Exception as exc:
        utils.logger.warning("[config_store.ensure_app_config_table] skipped: %s", exc)
        return False
    finally:
        if prev is not None:
            config.SAVE_DATA_OPTION = prev


async def get_app_config_row(config_key: str) -> Optional[Dict[str, Any]]:
    db_opt = _active_db_option()
    if not db_opt:
        return None
    prev = getattr(config, "SAVE_DATA_OPTION", None)
    try:
        config.SAVE_DATA_OPTION = db_opt
        async with get_session() as session:
            if session is None:
                return None
            result = await session.execute(
                select(AppConfig).where(AppConfig.config_key == config_key)
            )
            row = result.scalars().first()
            if not row:
                return None
            return {
                "config_key": row.config_key,
                "config_value": row.config_value or "",
                "platform": row.platform or "",
                "description": row.description or "",
                "status": row.status or "unknown",
                "last_checked_at": row.last_checked_at or "",
                "last_error": row.last_error or "",
                "updated_at": int(row.updated_at or 0),
            }
    except Exception as exc:
        utils.logger.debug("[config_store.get_app_config_row] %s unavailable: %s", config_key, exc)
        return None
    finally:
        if prev is not None:
            config.SAVE_DATA_OPTION = prev


async def upsert_app_config(
    *,
    config_key: str,
    config_value: Optional[str] = None,
    platform: str = "",
    description: str = "",
    status: Optional[str] = None,
    last_checked_at: Optional[str] = None,
    last_error: Optional[str] = None,
) -> Dict[str, Any]:
    db_opt = _active_db_option()
    if not db_opt:
        raise RuntimeError("当前未启用数据库存储模式（SAVE_DATA_OPTION 需为 postgres/sqlite/mysql）")

    await ensure_app_config_table()
    prev = getattr(config, "SAVE_DATA_OPTION", None)
    try:
        config.SAVE_DATA_OPTION = db_opt
        async with get_session() as session:
            if session is None:
                raise RuntimeError("无法获取数据库连接")
            result = await session.execute(
                select(AppConfig).where(AppConfig.config_key == config_key)
            )
            row = result.scalars().first()
            now_ms = utils.get_current_timestamp()
            if not row:
                row = AppConfig(
                    config_key=config_key,
                    config_value=_strip_cookie(config_value) if config_value is not None else "",
                    platform=platform,
                    description=description,
                    status=status or "unknown",
                    last_checked_at=last_checked_at or "",
                    last_error=last_error or "",
                    updated_at=now_ms,
                )
                session.add(row)
            else:
                if config_value is not None:
                    row.config_value = _strip_cookie(config_value)
                    row.updated_at = now_ms
                    if status is None:
                        row.status = "unknown"
                        row.last_error = ""
                if platform:
                    row.platform = platform
                if description:
                    row.description = description
                if status is not None:
                    row.status = status
                if last_checked_at is not None:
                    row.last_checked_at = last_checked_at
                if last_error is not None:
                    row.last_error = last_error
            await session.commit()
            return {
                "config_key": row.config_key,
                "config_value": row.config_value or "",
                "platform": row.platform or "",
                "description": row.description or "",
                "status": row.status or "unknown",
                "last_checked_at": row.last_checked_at or "",
                "last_error": row.last_error or "",
                "updated_at": int(row.updated_at or 0),
            }
    finally:
        if prev is not None:
            config.SAVE_DATA_OPTION = prev


def _read_secret_file(path: str) -> str:
    if not path:
        return ""
    file_path = Path(path)
    if not file_path.is_file():
        return ""
    try:
        return _strip_cookie(file_path.read_text(encoding="utf-8"))
    except OSError:
        return ""


def _resolve_fallback_cookie(platform: str) -> Tuple[str, str]:
    """Resolve non-DB fallback cookie and its source label."""
    spec = PLATFORM_COOKIE_SPECS[platform]
    if platform == "xhs":
        from media_platform.xhs.cookies import default_runtime_cookie_file, default_secret_cookie_file

        candidates = []
        for source_name, path in (
            ("runtime_file", default_runtime_cookie_file()),
            ("secret_file", default_secret_cookie_file()),
        ):
            text = _read_secret_file(path)
            if text:
                try:
                    mtime = Path(path).stat().st_mtime
                except OSError:
                    mtime = 0.0
                candidates.append((mtime, text, source_name))
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1], candidates[0][2]

    if spec.secret_file_env:
        secret_path = os.getenv(spec.secret_file_env, "").strip() or spec.default_secret_file
        secret_val = _read_secret_file(secret_path)
        if secret_val:
            return secret_val, "secret_file"

    dotenv_map = {}
    try:
        dotenv_map = dotenv_values()
    except Exception:
        dotenv_map = {}

    for env_key in spec.env_keys:
        val = _strip_cookie(
            os.getenv(env_key)
            or str(dotenv_map.get(env_key) or "")
            or getattr(config, env_key, "")
        )
        if val:
            return val, f"env:{env_key}"

    crawler_cookies = _strip_cookie(os.getenv("CRAWLER_COOKIES") or getattr(config, "COOKIES", ""))
    if crawler_cookies and _looks_like_platform_cookie(platform, crawler_cookies):
        return crawler_cookies, "env:CRAWLER_COOKIES"
    return "", "none"


def _looks_like_platform_cookie(platform: str, cookie_str: str) -> bool:
    if not cookie_str:
        return False
    lower = cookie_str.lower()
    if platform == "bili":
        return "sessdata=" in lower or "dedeuserid=" in lower
    if platform == "xhs":
        return "a1=" in lower or "web_session=" in lower
    if platform == "gzh":
        return "wr_skey=" in lower or "wr_vid=" in lower
    if platform == "dy":
        return "sessionid=" in lower or "ttwid=" in lower or "odin_tt=" in lower
    return True


async def resolve_platform_cookie_with_source(
    platform: str,
    explicit: Optional[str] = None,
) -> Tuple[str, str, Optional[Dict[str, Any]]]:
    """
    Resolve cookie in priority order:
    1) explicit request / CLI override
    2) app_config database row (non-empty)
    3) secret file / runtime file
    4) .env / environment variable
    """
    if platform not in PLATFORM_COOKIE_SPECS:
        return _strip_cookie(explicit), "explicit" if explicit else "none", None

    explicit_clean = _strip_cookie(explicit)
    if explicit_clean:
        return explicit_clean, "explicit", None

    spec = PLATFORM_COOKIE_SPECS[platform]
    row = await get_app_config_row(spec.config_key)
    if row and _strip_cookie(row.get("config_value")):
        return _strip_cookie(row["config_value"]), "database", row

    fallback_val, fallback_src = _resolve_fallback_cookie(platform)
    return fallback_val, fallback_src, row


async def resolve_platform_cookie(platform: str, explicit: Optional[str] = None) -> str:
    val, _, _ = await resolve_platform_cookie_with_source(platform, explicit=explicit)
    return val


async def get_db_cookie(platform: str) -> str:
    """Return only the DB-stored cookie override for a platform (empty if none)."""
    if platform not in PLATFORM_COOKIE_SPECS:
        return ""
    row = await get_app_config_row(PLATFORM_COOKIE_SPECS[platform].config_key)
    if not row:
        return ""
    return _strip_cookie(row.get("config_value"))


async def sync_refreshed_cookie_to_db(platform: str, cookie_str: str) -> None:
    """Best-effort update of an existing non-empty DB cookie after Set-Cookie rotation."""
    if platform not in PLATFORM_COOKIE_SPECS:
        return
    cleaned = _strip_cookie(cookie_str)
    if not cleaned or not _looks_like_platform_cookie(platform, cleaned):
        return
    spec = PLATFORM_COOKIE_SPECS[platform]
    row = await get_app_config_row(spec.config_key)
    if not row or not _strip_cookie(row.get("config_value")):
        return
    if _strip_cookie(row.get("config_value")) == cleaned:
        return
    try:
        await upsert_app_config(
            config_key=spec.config_key,
            config_value=cleaned,
            platform=platform,
            description=spec.label,
            status="valid",
            last_checked_at=_now_iso(),
            last_error="",
        )
    except Exception as exc:
        utils.logger.debug("[config_store.sync_refreshed_cookie_to_db] skipped: %s", exc)


async def apply_db_cookie_to_config(platform: str) -> str:
    """Load DB cookie for CLI / scheduled subprocesses when --cookies was not explicitly set."""
    if platform not in PLATFORM_COOKIE_SPECS:
        return getattr(config, "COOKIES", "")
    row = await get_app_config_row(PLATFORM_COOKIE_SPECS[platform].config_key)
    if not row or not _strip_cookie(row.get("config_value")):
        return getattr(config, "COOKIES", "")
    db_cookie = _strip_cookie(row["config_value"])
    config.COOKIES = db_cookie
    if platform == "dy":
        config.DY_COOKIES = db_cookie
    elif platform == "bili":
        config.BILI_COOKIES = db_cookie
    elif platform == "xhs":
        config.XHS_COOKIES = db_cookie
    elif platform == "gzh":
        config.WEREAD_WEB_COOKIE = db_cookie
        config.GZH_WEB_COOKIE = db_cookie
    return db_cookie


async def save_platform_cookie(
    platform: str,
    cookie_value: str,
    *,
    run_probe: bool = True,
) -> Dict[str, Any]:
    if platform not in PLATFORM_COOKIE_SPECS:
        raise ValueError(f"Unsupported platform: {platform}")
    spec = PLATFORM_COOKIE_SPECS[platform]
    cleaned = _strip_cookie(cookie_value)
    if not cleaned:
        raise ValueError("Cookie 内容不能为空")

    row = await upsert_app_config(
        config_key=spec.config_key,
        config_value=cleaned,
        platform=platform,
        description=spec.label,
        status="unknown",
        last_error="",
    )

    if platform == "xhs":
        from media_platform.xhs.cookies import persist_xhs_cookies

        persist_xhs_cookies(cleaned)

    if run_probe:
        probe_res = await probe_platform_cookie(platform, cookie_override=cleaned)
        row = await upsert_app_config(
            config_key=spec.config_key,
            platform=platform,
            description=spec.label,
            status=probe_res["status"],
            last_checked_at=probe_res["checked_at"],
            last_error=probe_res["message"],
        )

    return _build_status_item(spec, cleaned, "database", row)


async def clear_platform_cookie(platform: str) -> Dict[str, Any]:
    if platform not in PLATFORM_COOKIE_SPECS:
        raise ValueError(f"Unsupported platform: {platform}")
    spec = PLATFORM_COOKIE_SPECS[platform]
    await upsert_app_config(
        config_key=spec.config_key,
        config_value="",
        platform=platform,
        description=spec.label,
        status="unknown",
        last_checked_at="",
        last_error="已清空数据库配置，回退环境变量/Secret 文件",
    )
    val, source, row = await resolve_platform_cookie_with_source(platform)
    return _build_status_item(spec, val, source, row)


async def probe_platform_cookie(
    platform: str,
    cookie_override: Optional[str] = None,
) -> Dict[str, Any]:
    if platform not in PLATFORM_COOKIE_SPECS:
        raise ValueError(f"Unsupported platform: {platform}")
    spec = PLATFORM_COOKIE_SPECS[platform]
    checked_at = _now_iso()
    cookie_str, source, _ = await resolve_platform_cookie_with_source(
        platform, explicit=cookie_override
    )
    if not cookie_str:
        res = {"valid": False, "status": "expired", "message": "未配置 Cookie", "checked_at": checked_at}
        if cookie_override is None and await get_app_config_row(spec.config_key):
            await upsert_app_config(
                config_key=spec.config_key,
                status=res["status"],
                last_checked_at=checked_at,
                last_error=res["message"],
            )
        return res

    status = "unknown"
    valid = False
    message = ""

    try:
        if platform == "bili":
            from media_platform.bilibili.client import BilibiliClient

            client = BilibiliClient(
                headers={
                    "User-Agent": utils.get_user_agent(),
                    "Cookie": cookie_str,
                    "Origin": "https://www.bilibili.com",
                    "Referer": "https://www.bilibili.com",
                },
                playwright_page=None,
                cookie_dict=utils.convert_str_cookie_to_dict(cookie_str),
            )
            valid = bool(await asyncio.wait_for(client.pong(), timeout=15.0))
            status = "valid" if valid else "expired"
            message = "B站登录态有效" if valid else "B站 Cookie 已失效或未登录"

        elif platform == "xhs":
            from media_platform.xhs.client import XiaoHongShuClient
            from media_platform.xhs.exception import CookieExpiredError, PlatformAccessError

            client = XiaoHongShuClient(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                    ),
                    "Cookie": cookie_str,
                    "Origin": "https://www.xiaohongshu.com",
                    "Referer": "https://www.xiaohongshu.com/",
                    "Content-Type": "application/json;charset=UTF-8",
                },
                playwright_page=None,
                cookie_dict=utils.convert_str_cookie_to_dict(cookie_str),
                persist_cookies=False,
            )
            try:
                valid = bool(await asyncio.wait_for(client.pong(), timeout=20.0))
                status = "valid" if valid else "expired"
                message = "小红书 Cookie 有效" if valid else "小红书 Cookie 无效或已过期"
            except CookieExpiredError as exc:
                valid, status, message = False, "expired", f"小红书 Cookie 已过期: {exc}"
            except PlatformAccessError as exc:
                valid, status, message = False, "expired", f"小红书访问受限: {exc}"

        elif platform == "dy":
            cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
            has_session = bool(cookie_dict.get("sessionid") or cookie_dict.get("LOGIN_STATUS") == "1")
            has_ttwid = bool(cookie_dict.get("ttwid"))
            if not has_session and not has_ttwid:
                valid, status, message = False, "expired", "缺少抖音 sessionid / ttwid 字段"
            else:
                # Best-effort live check using DouYinClient if sign service is reachable
                sample_uid = await _find_sample_douyin_uid()
                if sample_uid:
                    from media_platform.douyin.client import DouYinClient

                    client = DouYinClient(
                        headers={
                            "User-Agent": (
                                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                            ),
                            "Cookie": cookie_str,
                            "Host": "www.douyin.com",
                            "Referer": "https://www.douyin.com/",
                            "Origin": "https://www.douyin.com/",
                        },
                        cookie_dict=cookie_dict,
                    )
                    try:
                        info = await asyncio.wait_for(client.get_user_info(sample_uid), timeout=15.0)
                        if isinstance(info, dict) and info.get("user"):
                            valid, status, message = True, "valid", "抖音 Cookie 实时接口探测有效"
                        else:
                            valid, status, message = False, "expired", "抖音接口未返回用户资料，可能触发风控或 Cookie 过期"
                    except Exception as exc:
                        valid = has_session
                        status = "valid" if has_session else "unknown"
                        message = f"格式有效（实时探测跳过/失败: {exc}）"
                else:
                    valid = has_session
                    status = "valid" if has_session else "unknown"
                    message = "格式校验通过（含 sessionid）" if has_session else "含 ttwid，缺少 sessionid（可能为访客态）"

        elif platform == "gzh":
            cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
            if not (cookie_dict.get("wr_skey") and cookie_dict.get("wr_vid")):
                valid, status, message = False, "expired", "缺少 wr_vid 或 wr_skey 字段"
            else:
                from media_platform.gzh.weread_cli import WereadCliError, WereadOmniBridge

                try:
                    bridge = WereadOmniBridge(web_cookie=cookie_str)
                    test_account = await _find_sample_gzh_account_id() or "MP_WXS_3913422171"
                    res = await asyncio.wait_for(
                        bridge.article_stats(test_account, limit=1), timeout=25.0
                    )
                    if isinstance(res, dict) and "articles" in res:
                        valid, status, message = True, "valid", "微信读书 Web Cookie 有效"
                    else:
                        valid, status, message = False, "expired", "未获取到文章阅读量数据"
                except WereadCliError as exc:
                    err_text = str(exc)
                    if "not found" in err_text.lower():
                        valid, status, message = True, "unknown", "格式校验通过（当前容器未安装 weread-omni CLI，请在 8088 端口探测）"
                    else:
                        valid, status, message = False, "expired", f"微信读书探测失败: {err_text}"
    except Exception as exc:
        valid, status, message = False, "expired", f"探测异常: {exc}"

    if cookie_override is None and await get_app_config_row(spec.config_key):
        await upsert_app_config(
            config_key=spec.config_key,
            status=status,
            last_checked_at=checked_at,
            last_error="" if valid else message,
        )

    return {
        "valid": valid,
        "status": status,
        "message": message,
        "checked_at": checked_at,
        "source": source,
    }


async def _find_sample_douyin_uid() -> Optional[str]:
    try:
        async with get_session() as session:
            if session is None:
                return None
            result = await session.execute(
                select(DouyinCreator.user_id).order_by(DouyinCreator.id.asc()).limit(1)
            )
            val = result.scalar()
            return str(val).strip() if val else None
    except Exception:
        return None


async def _find_sample_gzh_account_id() -> Optional[str]:
    try:
        async with get_session() as session:
            if session is None:
                return None
            result = await session.execute(
                select(GzhAccount.account_id).order_by(GzhAccount.id.asc()).limit(1)
            )
            val = result.scalar()
            return str(val).strip() if val else None
    except Exception:
        return None


def _build_status_item(
    spec: PlatformCookieSpec,
    cookie_val: str,
    source: str,
    row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    has_db_override = bool(row and _strip_cookie(row.get("config_value")))
    updated_ts = int(row.get("updated_at") or 0) if row else 0
    updated_at_iso = (
        datetime.fromtimestamp(updated_ts / 1000.0, tz=SHANGHAI_TZ).isoformat(timespec="seconds")
        if updated_ts > 0
        else ""
    )
    return {
        "platform": spec.platform,
        "config_key": spec.config_key,
        "label": spec.label,
        "hint": spec.hint,
        "configured": bool(cookie_val),
        "source": source,
        "has_db_override": has_db_override,
        "masked_cookie": mask_cookie(cookie_val),
        "length": len(cookie_val),
        "status": (row.get("status") if row else "unknown") or "unknown",
        "last_checked_at": (row.get("last_checked_at") if row else "") or "",
        "last_error": (row.get("last_error") if row else "") or "",
        "updated_at": updated_at_iso,
    }


async def list_platform_cookie_statuses() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for platform, spec in PLATFORM_COOKIE_SPECS.items():
        val, source, row = await resolve_platform_cookie_with_source(platform)
        items.append(_build_status_item(spec, val, source, row))
    return items
