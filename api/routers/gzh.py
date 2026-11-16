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
from media_platform.gzh.core import GzhCrawler
from media_platform.gzh.weread_cli import (
    WereadCliError,
    WereadOmniBridge,
    normalize_account_id,
)
from var import crawler_type_var, reset_gzh_account_stats_seen

router = APIRouter(prefix="/gzh", tags=["gzh"])


class AddAccountRequest(BaseModel):
    account_id: Optional[str] = Field(
        default=None,
        description="公众号 ID，例如 MP_WXS_2390745668；与 keyword 二选一",
    )
    keyword: Optional[str] = Field(
        default=None,
        description="按名称搜索公众号（weread search books --scope 2），取第一条",
    )
    fetch_articles: bool = Field(default=True, description="是否拉取文章列表与阅读量")
    max_articles: int = Field(default=20, ge=1, le=100, description="最大文章数")
    web_cookie: Optional[str] = Field(
        default=None,
        description="可选；覆盖 WEREAD_WEB_COOKIE / GZH_WEB_COOKIE",
    )


@router.post("/account/add")
async def add_gzh_account(req: AddAccountRequest):
    """
    添加公众号账号并入库 gzh_account；
    可选拉取文章列表与阅读量写入 gzh_article，并追加 gzh_account_stats。
    """
    crawler_type_var.set("api_add")
    reset_gzh_account_stats_seen()

    account_id = (req.account_id or "").strip()
    keyword = (req.keyword or "").strip()
    if not account_id and not keyword:
        raise HTTPException(status_code=400, detail="请提供 account_id 或 keyword")

    try:
        bridge = WereadOmniBridge(web_cookie=req.web_cookie)
    except WereadCliError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not account_id and keyword:
        try:
            books = await bridge.search_accounts(keyword, count=1)
        except WereadCliError as exc:
            raise HTTPException(status_code=502, detail=f"搜索公众号失败: {exc}") from exc
        if not books:
            raise HTTPException(status_code=404, detail=f"未搜索到公众号: {keyword}")
        account_id = str(books[0].get("bookId") or books[0].get("accountId") or "")
        if not account_id:
            raise HTTPException(status_code=404, detail="搜索结果缺少 bookId")

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
        result = await crawler.crawl_one_account(
            account_id,
            fetch_articles=req.fetch_articles,
            max_articles=req.max_articles,
            write_account_stats=req.fetch_articles,
            source_type="api_add",
        )
    except WereadCliError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"采集入库失败: {exc}") from exc

    warnings = result.get("warnings") or []
    message = "公众号信息解析并入库成功"
    if warnings and not result.get("stats_saved"):
        message = "公众号已入库，但阅读量拉取失败（请更新 WEREAD_WEB_COOKIE）"
    return {
        "code": 200,
        "message": message,
        "data": {
            "account_id": result.get("account_id"),
            "nickname": result.get("nickname"),
            "articles_saved": result.get("articles_saved", 0),
            "stats_saved": bool(result.get("stats_saved")),
            "warnings": warnings,
            "weread_cli": getattr(config, "WEREAD_OMNI_CLI", ""),
        },
    }
