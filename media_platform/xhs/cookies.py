# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""Xiaohongshu cookie resolve / persist helpers.

Why this exists:
- Pure-API mode sends Cookie via request headers and previously ignored Set-Cookie,
  so rotated web_session / a1 / websectiga quickly went stale.
- Docker injects XHS_COOKIES as an environment variable; updating .env alone does
  not refresh a running container unless recreated.
- Mirror the WeRead secret-file pattern: hot-read a file each request, and persist
  refreshed cookies to a writable runtime file under /app/data.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple

import config
from tools import utils

_persist_lock = threading.Lock()


def _strip_cookie(value: Optional[str]) -> str:
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    return text


def _reload_dotenv() -> None:
    try:
        from dotenv import find_dotenv, load_dotenv

        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path, override=True)
    except Exception:
        pass


def looks_like_xhs_cookies(cookie_str: str) -> bool:
    lower = (cookie_str or "").lower()
    return "a1=" in lower or "web_session=" in lower


def cookie_dict_to_str(cookie_dict: Dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookie_dict.items() if k and v is not None)


def merge_cookie_dict(
    base: Dict[str, str], updates: Dict[str, str]
) -> Tuple[Dict[str, str], bool]:
    """Merge cookie updates; return (merged_dict, changed)."""
    merged = dict(base or {})
    changed = False
    for name, value in (updates or {}).items():
        if not name or value is None:
            continue
        value_str = str(value)
        if merged.get(name) != value_str:
            merged[name] = value_str
            changed = True
    return merged, changed


def default_secret_cookie_file() -> str:
    return (
        os.getenv("XHS_COOKIES_FILE", "").strip()
        or "/run/secrets/xhs_cookies"
    )


def default_runtime_cookie_file() -> str:
    return (
        os.getenv("XHS_COOKIES_RUNTIME_FILE", "").strip()
        or "/app/data/xhs_cookies"
    )


def _read_cookie_file(path: str) -> Tuple[str, float]:
    if not path:
        return "", 0.0
    cookie_path = Path(path)
    if not cookie_path.is_file():
        return "", 0.0
    try:
        mtime = cookie_path.stat().st_mtime
        return _strip_cookie(cookie_path.read_text(encoding="utf-8")), mtime
    except OSError as exc:
        utils.logger.warning("[xhs.cookies] cannot read cookie file %s: %s", path, exc)
        return "", 0.0


def _pick_newer_file_cookie() -> str:
    """Prefer the newer of runtime (auto-refreshed) vs secret (manual) cookie files."""
    runtime_path = default_runtime_cookie_file()
    secret_path = default_secret_cookie_file()
    runtime_cookie, runtime_mtime = _read_cookie_file(runtime_path)
    secret_cookie, secret_mtime = _read_cookie_file(secret_path)

    candidates = []
    if runtime_cookie and looks_like_xhs_cookies(runtime_cookie):
        candidates.append((runtime_mtime, runtime_cookie, runtime_path))
    if secret_cookie and looks_like_xhs_cookies(secret_cookie):
        candidates.append((secret_mtime, secret_cookie, secret_path))
    if not candidates:
        return ""

    candidates.sort(key=lambda item: item[0], reverse=True)
    chosen_mtime, chosen_cookie, chosen_path = candidates[0]
    utils.logger.debug(
        "[xhs.cookies] using cookie file %s (mtime=%s)", chosen_path, chosen_mtime
    )
    return chosen_cookie


def resolve_xhs_cookies(cookies_str: Optional[str] = None) -> str:
    """
    Resolve Xiaohongshu cookies.

    Priority:
    1) request body cookies
    2) newer of XHS_COOKIES_RUNTIME_FILE / XHS_COOKIES_FILE (hot-read)
    3) XHS_COOKIES from env (dotenv reloaded) / config
    4) config.COOKIES / CRAWLER_COOKIES when it looks like XHS cookies
    """
    request_cookies = _strip_cookie(cookies_str)
    if request_cookies and looks_like_xhs_cookies(request_cookies):
        return request_cookies

    file_cookies = _pick_newer_file_cookie()
    if file_cookies:
        return file_cookies

    _reload_dotenv()
    env_cookies = _strip_cookie(
        os.getenv("XHS_COOKIES")
        or getattr(config, "XHS_COOKIES", None)
        or ""
    )
    if env_cookies and looks_like_xhs_cookies(env_cookies):
        return env_cookies

    fallback = _strip_cookie(
        os.getenv("CRAWLER_COOKIES")
        or getattr(config, "COOKIES", None)
        or ""
    )
    if fallback and looks_like_xhs_cookies(fallback):
        return fallback
    return ""


def persist_xhs_cookies(cookie_str: str, path: Optional[str] = None) -> bool:
    """Atomically persist refreshed cookies to the runtime file (best-effort)."""
    cookie_str = _strip_cookie(cookie_str)
    if not cookie_str or not looks_like_xhs_cookies(cookie_str):
        return False

    target = path or default_runtime_cookie_file()
    if not target:
        return False

    target_path = Path(target)
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_suffix(target_path.suffix + ".next")
        with _persist_lock:
            tmp_path.write_text(cookie_str, encoding="utf-8")
            os.chmod(tmp_path, 0o600)
            tmp_path.replace(target_path)
        utils.logger.info("[xhs.cookies] persisted refreshed cookies to %s", target)
        return True
    except OSError as exc:
        utils.logger.warning(
            "[xhs.cookies] failed to persist cookies to %s: %s", target, exc
        )
        return False


def cookie_update_hint() -> str:
    secret = default_secret_cookie_file()
    runtime = default_runtime_cookie_file()
    return (
        f"请原子替换 Cookie 文件后重试（推荐 heredoc，避免 Cookie 中 %22 被 printf 当成格式符）："
        f"cat > ./secrets/xhs_cookies.next <<'EOF' … EOF && "
        f"mv ./secrets/xhs_cookies.next ./secrets/xhs_cookies ；"
        f"容器内路径 {secret} 热加载，无需重建容器。"
        f"若存在自动刷新缓存 {runtime}，更新 secret 后可删除该缓存文件。"
    )
