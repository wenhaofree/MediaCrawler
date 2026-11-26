# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import config
from database.config_store import resolve_platform_cookie
from media_platform.gzh.core import GzhCrawler
from media_platform.gzh.weread_cli import (
    WereadCliError,
    WereadOmniBridge,
    biz_from_account_id,
    normalize_account_id,
    validate_article_url,
)
from var import crawler_type_var, reset_gzh_account_stats_seen

router = APIRouter(prefix="/gzh", tags=["gzh"])


class InspectArticleRequest(BaseModel):
    article_url: str = Field(
        ...,
        description="微信公众号文章链接，必须符合 https://mp.weixin.qq.com/s?... 且包含明确的 __biz=",
    )
    save_account: bool = Field(
        default=False,
        description="是否将解析到的公众号信息同步入库 gzh_account",
    )


class AddAccountRequest(BaseModel):
    account_id: Optional[str] = Field(
        default=None,
        description="公众号 ID，例如 MP_WXS_2390745668；与 keyword、article_url 三选一",
    )
    keyword: Optional[str] = Field(
        default=None,
        description="按名称搜索公众号（weread search books --scope 2），取第一条",
    )
    article_url: Optional[str] = Field(
        default=None,
        description="微信公众号文章链接，必须符合 https://mp.weixin.qq.com/s?... 且包含明确的 __biz=",
    )
    fetch_articles: bool = Field(default=True, description="是否拉取文章列表与阅读量")
    max_articles: int = Field(default=20, ge=1, le=100, description="最大文章数")
    web_cookie: Optional[str] = Field(
        default=None,
        description="可选；覆盖 WEREAD_WEB_COOKIE / GZH_WEB_COOKIE",
    )


@router.post("/article/inspect")
async def inspect_gzh_article(req: InspectArticleRequest):
    """
    根据公众号文章链接（必须包含明确的 __biz=）反查对应的公众号作者信息，
    可选同步将该公众号写入 gzh_account。
    """
    crawler_type_var.set("api_inspect")
    try:
        normalized_url = validate_article_url(req.article_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        bridge = WereadOmniBridge()
    except WereadCliError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    crawler = GzhCrawler()
    crawler.bridge = bridge
    try:
        if req.save_account:
            result = await crawler.crawl_by_article_url(
                normalized_url,
                fetch_articles=False,
                source_type="api_inspect",
            )
            account_data = {
                "account_id": result.get("account_id"),
                "biz": result.get("biz"),
                "biz_numeric_id": result.get("biz_numeric_id"),
                "nickname": result.get("nickname"),
                "author": result.get("author"),
                "avatar": result.get("avatar"),
                "category": result.get("category"),
                "desc": result.get("desc"),
                "deep_link": result.get("deep_link"),
                "reader_link": result.get("reader_link"),
                "entity_subject": None,
                "entity_subject_available": False,
            }
            article_data = result.get("inspected_article")
            source = result.get("source")
            diagnostics = result.get("diagnostics") or []
        else:
            resolved = await crawler.resolve_account_from_article(
                normalized_url,
                enrich_book_info=True,
            )
            account_data = resolved["account"]
            article_data = resolved.get("article")
            source = resolved.get("source")
            diagnostics = resolved.get("diagnostics") or []
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WereadCliError as exc:
        raise HTTPException(status_code=502, detail=f"根据文章解析公众号失败: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"根据文章解析公众号失败: {exc}") from exc

    return {
        "code": 200,
        "message": "根据文章解析公众号信息成功",
        "data": {
            "input_url": normalized_url,
            "source": source,
            "account": account_data,
            "article": article_data,
            "diagnostics": diagnostics,
            "saved": bool(req.save_account),
            "weread_cli": getattr(config, "WEREAD_OMNI_CLI", ""),
        },
    }


@router.post("/account/add")
async def add_gzh_account(req: AddAccountRequest):
    """
    添加公众号账号并入库 gzh_account（支持 account_id、keyword 或严格符合规则的文章链接 article_url）；
    可选拉取文章列表与阅读量写入 gzh_article，并追加 gzh_account_stats。
    """
    crawler_type_var.set("api_add")
    reset_gzh_account_stats_seen()

    account_id = (req.account_id or "").strip()
    keyword = (req.keyword or "").strip()
    article_url = (req.article_url or "").strip()
    if not account_id and not keyword and not article_url:
        raise HTTPException(status_code=400, detail="请提供 account_id、keyword 或 article_url")

    normalized_article_url = ""
    if not account_id and article_url:
        try:
            normalized_article_url = validate_article_url(article_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    effective_web_cookie = await resolve_platform_cookie("gzh", explicit=req.web_cookie)
    try:
        bridge = WereadOmniBridge(web_cookie=effective_web_cookie or req.web_cookie)
    except WereadCliError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not account_id and not normalized_article_url and keyword:
        try:
            books = await bridge.search_accounts(keyword, count=1)
        except WereadCliError as exc:
            raise HTTPException(status_code=502, detail=f"搜索公众号失败: {exc}") from exc
        if not books:
            raise HTTPException(status_code=404, detail=f"未搜索到公众号: {keyword}")
        account_id = str(books[0].get("bookId") or books[0].get("accountId") or "")
        if not account_id:
            raise HTTPException(status_code=404, detail="搜索结果缺少 bookId")

    if account_id:
        try:
            account_id = normalize_account_id(account_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if req.fetch_articles and not bridge.web_cookie:
        raise HTTPException(
            status_code=400,
            detail="拉取阅读量需要配置 WEREAD_WEB_COOKIE 或在请求体传入 web_cookie",
        )

    crawler = GzhCrawler()
    crawler.bridge = bridge
    try:
        if normalized_article_url and not account_id:
            result = await crawler.crawl_by_article_url(
                normalized_article_url,
                fetch_articles=req.fetch_articles,
                max_articles=req.max_articles,
                write_account_stats=req.fetch_articles,
                source_type="api_add",
            )
        else:
            result = await crawler.crawl_one_account(
                account_id,
                fetch_articles=req.fetch_articles,
                max_articles=req.max_articles,
                write_account_stats=req.fetch_articles,
                source_type="api_add",
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WereadCliError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"采集入库失败: {exc}") from exc

    resolved_account_id = str(result.get("account_id") or account_id or "")
    biz_info = biz_from_account_id(resolved_account_id) if resolved_account_id else {}
    warnings = result.get("warnings") or []
    message = "公众号信息解析并入库成功"
    if warnings and not result.get("stats_saved"):
        message = "公众号已入库，但阅读量拉取失败（请更新 WEREAD_WEB_COOKIE）"
    return {
        "code": 200,
        "message": message,
        "data": {
            "account_id": resolved_account_id,
            "biz": result.get("biz") or biz_info.get("biz"),
            "biz_numeric_id": result.get("biz_numeric_id") or biz_info.get("biz_numeric_id"),
            "nickname": result.get("nickname"),
            "author": result.get("author"),
            "avatar": result.get("avatar"),
            "category": result.get("category"),
            "desc": result.get("desc"),
            "deep_link": result.get("deep_link"),
            "reader_link": result.get("reader_link"),
            "inspected_article": result.get("inspected_article"),
            "articles_saved": result.get("articles_saved", 0),
            "stats_saved": bool(result.get("stats_saved")),
            "warnings": warnings,
            "weread_cli": getattr(config, "WEREAD_OMNI_CLI", ""),
        },
    }
