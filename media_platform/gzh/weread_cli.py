# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse, urlunparse

import config
from tools import utils

ACCOUNT_ID_RE = re.compile(r"^MP_WXS_\d+$")


class WereadCliError(RuntimeError):
    """Raised when weread-omni CLI fails or returns invalid JSON."""


def normalize_account_id(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ValueError("account_id cannot be empty")
    if ACCOUNT_ID_RE.match(value):
        return value
    # Allow bare numeric suffix
    if value.isdigit():
        return f"MP_WXS_{value}"
    match = re.search(r"(MP_WXS_\d+)", value)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid WeRead public-account id: {raw!r} (expect MP_WXS_*)")


def normalize_published_at(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    # milliseconds → seconds
    if ts > 10_000_000_000:
        ts = ts // 1000
    return ts


def _candidate_cli_paths() -> List[str]:
    return [
        str(Path("/opt/weread-omni/bin/weread-omni.js")),
        str(Path.home() / "github" / "weread-omni" / "bin" / "weread-omni.js"),
        str(Path("/Users/wenhao/fuwenhao/temp/demo-weread/weread-omni/bin/weread-omni.js")),
    ]


def resolve_cli_path(cli_path: Optional[str] = None) -> str:
    """
    Resolve weread-omni launcher path.
    Prefer explicit path when it exists; otherwise fall back to known local layouts.
    """
    configured = (cli_path or getattr(config, "WEREAD_OMNI_CLI", "") or "").strip()
    candidates: List[str] = []
    if configured:
        candidates.append(configured)
    candidates.extend(_candidate_cli_paths())
    candidates.append("weread-omni")

    seen: set[str] = set()
    missing_configured = False
    for path in candidates:
        if not path or path in seen:
            continue
        seen.add(path)
        if os.path.sep in path or path.startswith("."):
            if os.path.exists(path):
                if configured and path != configured and missing_configured:
                    utils.logger.warning(
                        f"[WereadOmniBridge] WEREAD_OMNI_CLI={configured!r} missing; "
                        f"fallback to {path}"
                    )
                return path
            if path == configured:
                missing_configured = True
            continue
        found = shutil.which(path)
        if found:
            if configured and missing_configured:
                utils.logger.warning(
                    f"[WereadOmniBridge] WEREAD_OMNI_CLI={configured!r} missing; "
                    f"fallback to {found}"
                )
            return found

    raise WereadCliError(
        "weread-omni CLI not found. Build weread-omni and set WEREAD_OMNI_CLI "
        "to bin/weread-omni.js (local: .../weread-omni/bin/weread-omni.js; "
        "server: /opt/weread-omni/bin/weread-omni.js)."
    )


def _strip_cookie(value: Optional[str]) -> str:
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    return text


def _read_cookie_file(path: str) -> str:
    if not path:
        return ""
    cookie_path = Path(path)
    if not cookie_path.is_file():
        return ""
    try:
        return _strip_cookie(cookie_path.read_text(encoding="utf-8"))
    except OSError as exc:
        utils.logger.warning("[WereadOmniBridge] cannot read cookie file %s: %s", path, exc)
        return ""


def resolve_web_cookie(cookie: Optional[str] = None) -> str:
    """
    Resolve WeRead web cookie for article-stats.

    Priority (runtime env first, so updating .env / export works without stale config):
    1) request body cookie
    2) WEREAD_WEB_COOKIE_FILE (re-read for each request, for Docker secret mounts)
    3) WEREAD_WEB_COOKIE (same var as weread-omni CLI)
    4) GZH_WEB_COOKIE
    5) config.GZH_WEB_COOKIE / config fallbacks
    """
    try:
        from dotenv import load_dotenv, find_dotenv

        # Pick up latest .env without requiring process restart for cookie rotation.
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path, override=True)
    except Exception:
        pass

    return (
        _strip_cookie(cookie)
        or _read_cookie_file(os.getenv("WEREAD_WEB_COOKIE_FILE", "").strip())
        or _strip_cookie(os.getenv("WEREAD_WEB_COOKIE"))
        or _strip_cookie(os.getenv("GZH_WEB_COOKIE"))
        or _strip_cookie(getattr(config, "GZH_WEB_COOKIE", None))
        or _strip_cookie(getattr(config, "WEREAD_WEB_COOKIE", None))
    )


class WereadOmniBridge:
    """Thin subprocess wrapper around weread-omni --json commands."""

    def __init__(
        self,
        *,
        cli_path: Optional[str] = None,
        web_cookie: Optional[str] = None,
        account_alias: Optional[str] = None,
        timeout_sec: Optional[float] = None,
    ):
        self.cli_path = resolve_cli_path(cli_path)
        # Keep explicit request cookie separately; env cookie is re-read per stats call.
        self._request_cookie = _strip_cookie(web_cookie)
        self.web_cookie = resolve_web_cookie(self._request_cookie or None)
        self.account_alias = (
            account_alias
            if account_alias is not None
            else (getattr(config, "GZH_WEREAD_ACCOUNT", "") or "")
        ).strip()
        self.timeout_sec = float(
            timeout_sec
            if timeout_sec is not None
            else getattr(config, "GZH_CLI_TIMEOUT_SEC", 120)
        )

    def _base_cmd(self) -> List[str]:
        cmd = [self.cli_path, "--json"]
        if self.account_alias:
            cmd.extend(["--account", self.account_alias])
        return cmd

    async def run_json(self, args: List[str], *, need_web_cookie: bool = False) -> Any:
        cmd = self._base_cmd() + list(args)
        env = os.environ.copy()
        if need_web_cookie:
            # Re-resolve each call so rotated .env / shell export takes effect.
            self.web_cookie = resolve_web_cookie(self._request_cookie or None)
            if not self.web_cookie:
                raise WereadCliError(
                    "Missing WEREAD_WEB_COOKIE / GZH_WEB_COOKIE for article-stats"
                )
            env["WEREAD_WEB_COOKIE"] = self.web_cookie
            skey = ""
            for part in self.web_cookie.split(";"):
                part = part.strip()
                if part.lower().startswith("wr_skey="):
                    skey = part.split("=", 1)[1][:6]
                    break
            utils.logger.info(
                f"[WereadOmniBridge] article-stats using WEREAD_WEB_COOKIE wr_skey={skey}..."
            )

        utils.logger.info(f"[WereadOmniBridge] exec: {' '.join(cmd[:6])} ...")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout_sec
            )
        except asyncio.TimeoutError as exc:
            raise WereadCliError(
                f"weread-omni timed out after {self.timeout_sec}s: {' '.join(args)}"
            ) from exc
        except FileNotFoundError as exc:
            raise WereadCliError(f"Failed to start CLI: {self.cli_path}") from exc

        stdout = (stdout_b or b"").decode("utf-8", errors="replace").strip()
        stderr = (stderr_b or b"").decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            detail = stdout or stderr or f"exit={proc.returncode}"
            try:
                err_obj = json.loads(detail)
                detail = err_obj.get("error") or detail
            except Exception:
                pass
            raise WereadCliError(f"weread-omni failed ({' '.join(args)}): {detail}")

        if not stdout:
            raise WereadCliError(f"weread-omni returned empty stdout for {' '.join(args)}")
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise WereadCliError(
                f"Invalid JSON from weread-omni: {stdout[:300]}"
            ) from exc

    async def book_info(self, account_id: str) -> Dict[str, Any]:
        account_id = normalize_account_id(account_id)
        data = await self.run_json(["book", "info", account_id])
        return data if isinstance(data, dict) else {}

    async def search_accounts(self, keyword: str, *, count: int = 10) -> List[Dict[str, Any]]:
        data = await self.run_json(["search", "books", keyword, "--scope", "2"])
        # CLI already gets --json from base; avoid duplicate
        books: List[Dict[str, Any]] = []
        if isinstance(data, dict):
            raw = data.get("books") or data.get("items") or []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                info = item.get("bookInfo") or item.get("book") or item
                if isinstance(info, dict) and info.get("bookInfo"):
                    info = info["bookInfo"]
                book_id = (
                    (info or {}).get("bookId")
                    or (info or {}).get("accountId")
                    or item.get("bookId")
                )
                if book_id and str(book_id).startswith("MP_WXS_"):
                    books.append(info if isinstance(info, dict) else item)
                if len(books) >= count:
                    break
        return books

    async def list_articles(
        self, account_id: str, *, count: int = 20, synckey: int = 0
    ) -> Dict[str, Any]:
        account_id = normalize_account_id(account_id)
        args = ["public-accounts", "articles", account_id, "--count", str(count)]
        if synckey is not None:
            args.extend(["--synckey", str(synckey)])
        data = await self.run_json(args)
        return data if isinstance(data, dict) else {}

    async def review_single(self, review_id: str) -> Dict[str, Any]:
        """Load review details, including mpInfo.doc_url when list results omit it."""
        data = await self.run_json(["review", "single", str(review_id)])
        review = data.get("review") if isinstance(data, dict) else None
        return review if isinstance(review, dict) else {}

    async def article_stats(
        self, account_id: str, *, limit: int = 20, offset: int = 0
    ) -> Dict[str, Any]:
        account_id = normalize_account_id(account_id)
        data = await self.run_json(
            [
                "public-accounts",
                "article-stats",
                account_id,
                "--limit",
                str(limit),
                "--offset",
                str(offset),
            ],
            need_web_cookie=True,
        )
        return data if isinstance(data, dict) else {}


def map_book_info_to_account(account_id: str, book: Dict[str, Any]) -> Dict[str, Any]:
    info = book.get("bookInfo") if isinstance(book.get("bookInfo"), dict) else book
    return {
        "account_id": normalize_account_id(
            account_id or info.get("bookId") or info.get("accountId") or ""
        ),
        "nickname": info.get("title") or info.get("nickname") or "",
        "author": info.get("author") or "",
        "avatar": info.get("cover") or info.get("avatar") or "",
        "category": info.get("category") or info.get("newRatingName") or "",
        "desc": info.get("intro") or info.get("desc") or "",
        "article_count": None,
    }


def _article_url(*values: Any) -> str:
    """Keep the real mp.weixin.qq.com article URL, unwrapping captcha redirects."""
    for value in values:
        url = str(value or "").strip()
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.hostname == "mp.weixin.qq.com" and parsed.path == "/mp/wappoc_appmsgcaptcha":
            url = (parse_qs(parsed.query).get("target_url") or [""])[0]
            parsed = urlparse(url)
        if parsed.hostname == "mp.weixin.qq.com" and (
            parsed.path == "/s" or parsed.path.startswith("/s/")
        ):
            return urlunparse(parsed._replace(fragment=""))
    return ""


def map_mobile_article(account_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    mp = item.get("mpInfo") if isinstance(item.get("mpInfo"), dict) else {}
    published = normalize_published_at(
        mp.get("time") or item.get("createTime") or item.get("publishedAt")
    )
    return {
        "review_id": str(item.get("reviewId") or item.get("review_id") or ""),
        "original_id": str(mp.get("originalId") or mp.get("original_id") or ""),
        "account_id": normalize_account_id(account_id),
        "title": mp.get("title") or item.get("title") or "",
        "summary": mp.get("content") or item.get("summary") or "",
        "account_name": mp.get("mp_name") or item.get("accountName") or "",
        "article_url": _article_url(
            mp.get("doc_url"), mp.get("docUrl"), mp.get("articleUrl"), mp.get("url"),
            item.get("doc_url"), item.get("docUrl"), item.get("articleUrl"), item.get("url"),
        ),
        "cover_url": mp.get("pic_url") or mp.get("picUrl") or "",
        "published_at": published,
        "read_count": None,
        "like_count": None,
    }


def map_stats_article(account_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "review_id": str(item.get("reviewId") or item.get("review_id") or ""),
        "original_id": str(item.get("originalId") or item.get("original_id") or ""),
        "account_id": normalize_account_id(account_id),
        "title": item.get("title") or "",
        "summary": item.get("summary") or "",
        "account_name": item.get("accountName") or "",
        "article_url": _article_url(
            item.get("articleUrl"), item.get("article_url"), item.get("doc_url"),
            item.get("docUrl"), item.get("url"),
        ),
        "cover_url": item.get("coverUrl") or item.get("pic_url") or "",
        "published_at": normalize_published_at(item.get("publishedAt") or item.get("time")),
        "read_count": item.get("readCount"),
        "like_count": item.get("likeCount"),
    }


def _article_merge_key(article: Dict[str, Any]) -> str:
    title = (article.get("title") or "").strip()
    published = article.get("published_at")
    account_id = (article.get("account_id") or "").strip()
    return f"{account_id}|{title}|{published if published is not None else ''}"


def _pick_nonempty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def merge_article_sources(
    mobile_articles: List[Dict[str, Any]],
    stats_articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge mobile list (cover/url) with stats list (read/like) into one row per article.
    Match key: account_id + title + published_at (then title-only fallback).
    """
    by_full: Dict[str, Dict[str, Any]] = {}
    by_title: Dict[str, Dict[str, Any]] = {}

    def _upsert(mapped: Dict[str, Any]) -> None:
        title = (mapped.get("title") or "").strip()
        if not title:
            return
        account_id = (mapped.get("account_id") or "").strip()
        full_key = _article_merge_key(mapped)
        title_key = f"{account_id}|{title}"
        existing = by_full.get(full_key) or by_title.get(title_key)
        if not existing:
            row = dict(mapped)
            by_full[full_key] = row
            by_title[title_key] = row
            return
        # Prefer stats review/original/read; prefer mobile cover/url.
        existing["review_id"] = _pick_nonempty(
            existing.get("review_id") if "_WR" in str(existing.get("review_id") or "") else None,
            mapped.get("review_id") if "_WR" in str(mapped.get("review_id") or "") else None,
            existing.get("review_id"),
            mapped.get("review_id"),
        )
        existing["original_id"] = _pick_nonempty(
            existing.get("original_id"), mapped.get("original_id")
        )
        existing["summary"] = _pick_nonempty(existing.get("summary"), mapped.get("summary"))
        existing["account_name"] = _pick_nonempty(
            existing.get("account_name"), mapped.get("account_name")
        )
        existing["article_url"] = _pick_nonempty(
            existing.get("article_url"), mapped.get("article_url")
        )
        existing["cover_url"] = _pick_nonempty(
            existing.get("cover_url"), mapped.get("cover_url")
        )
        if existing.get("published_at") is None:
            existing["published_at"] = mapped.get("published_at")
        if mapped.get("read_count") is not None:
            existing["read_count"] = mapped.get("read_count")
        if mapped.get("like_count") is not None:
            existing["like_count"] = mapped.get("like_count")
        by_full[_article_merge_key(existing)] = existing
        by_title[title_key] = existing

    for item in mobile_articles:
        _upsert(item)
    for item in stats_articles:
        _upsert(item)

    # Deduplicate by object identity while preserving order (stats-enriched first)
    ordered: List[Dict[str, Any]] = []
    seen_ids: set[int] = set()
    for row in list(by_full.values()):
        obj_id = id(row)
        if obj_id in seen_ids:
            continue
        seen_ids.add(obj_id)
        ordered.append(row)
    # Prefer rows that already have both cover + read
    ordered.sort(
        key=lambda r: (
            0 if (r.get("cover_url") and r.get("read_count") is not None) else 1,
            0 if r.get("read_count") is not None else 1,
            0 if r.get("cover_url") else 1,
        )
    )
    return ordered
