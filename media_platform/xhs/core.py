# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/core.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import random
from asyncio import Task
from typing import Dict, List, Optional

from tenacity import RetryError

import config
from base.base_crawler import AbstractCrawler
from media_downloader import MediaDownloader
from model.m_xiaohongshu import NoteUrlInfo, CreatorUrlInfo
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import xhs as xhs_store
from tools import utils
from var import crawler_type_var, reset_xhs_creator_stats_seen, source_keyword_var

from . import media as xhs_media
from .client import XiaoHongShuClient
from .cookies import resolve_xhs_cookies
from .exception import (
    CookieExpiredError,
    DataFetchError,
    IPBlockError,
    NoteNotFoundError,
    PlatformAccessError,
)
from .field import SearchSortType
from .help import parse_note_info_from_note_url, parse_creator_info_from_url, get_search_id


class XiaoHongShuCrawler(AbstractCrawler):
    xhs_client: XiaoHongShuClient

    def __init__(self) -> None:
        if config.XHS_INTERNATIONAL:
            self.index_url = "https://www.rednote.com"
            self.cookie_urls = [self.index_url, "https://webapi.rednote.com"]
        else:
            self.index_url = "https://www.xiaohongshu.com"
            self.cookie_urls = [self.index_url, "https://edith.xiaohongshu.com"]
        # self.user_agent = utils.get_user_agent()
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        self.ip_proxy_pool = None  # Proxy IP pool for automatic proxy refresh
        self._media_downloader: Optional[MediaDownloader] = None

    def _configure_safe_mode(self) -> None:
        if not config.XHS_SAFE_MODE:
            return
        config.MAX_CONCURRENCY_NUM = 1
        config.ENABLE_GET_COMMENTS = False
        config.ENABLE_GET_SUB_COMMENTS = False
        config.ENABLE_GET_MEDIA = False
        if config.CRAWLER_MAX_PAGES <= 0 or config.CRAWLER_MAX_PAGES > config.XHS_MAX_PAGES:
            config.CRAWLER_MAX_PAGES = config.XHS_MAX_PAGES
        config.XHS_CREATOR_ID_LIST = config.XHS_CREATOR_ID_LIST[: config.XHS_MAX_CREATORS_PER_RUN]
        utils.logger.info(
            "[XiaoHongShuCrawler] Safe mode enabled: one concurrent request, pages=%s, creators=%s, comments/media disabled",
            config.CRAWLER_MAX_PAGES,
            len(config.XHS_CREATOR_ID_LIST),
        )

    def _request_interval(self) -> float:
        return random.uniform(
            config.XHS_REQUEST_INTERVAL_MIN_SEC,
            config.XHS_REQUEST_INTERVAL_MAX_SEC,
        )

    async def _wait_between_requests(self, reason: str) -> None:
        seconds = self._request_interval()
        await asyncio.sleep(seconds)
        utils.logger.info("[XiaoHongShuCrawler] Slept %.1fs %s", seconds, reason)

    async def start(self) -> None:
        reset_xhs_creator_stats_seen()
        self._configure_safe_mode()
        httpx_proxy_format = None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            _, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        cookie_str = resolve_xhs_cookies() or config.COOKIES.strip()
        if not cookie_str:
            raise RuntimeError(
                "XHS pure API requires cookies via ./secrets/xhs_cookies or XHS_COOKIES"
            )
        if config.CRAWLER_TYPE == "creator" and not config.XHS_CREATOR_ID_LIST:
            raise RuntimeError("XHS creator crawl requires XHS_CREATOR_IDS or --creator_id")
        self.xhs_client = await self.create_xhs_client(httpx_proxy_format, cookie_str=cookie_str)
        try:
            if not await self.xhs_client.pong():
                raise RuntimeError(
                    "XHS Cookie is invalid or expired; update ./secrets/xhs_cookies "
                    "(hot reload, no container recreate) and retry"
                )
        except CookieExpiredError as exc:
            raise RuntimeError(
                f"XHS Cookie expired: {exc}; update ./secrets/xhs_cookies and retry"
            ) from exc

        crawler_type_var.set(config.CRAWLER_TYPE)
        if config.CRAWLER_TYPE == "search":
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            await self.get_specified_notes()
        elif config.CRAWLER_TYPE == "creator":
            await self.get_creators_and_notes()

        utils.logger.info("[XiaoHongShuCrawler.start] Xhs Crawler finished ...")

    async def search(self) -> None:
        """Search for notes and retrieve their comment information."""
        utils.logger.info("[XiaoHongShuCrawler.search] Begin search Xiaohongshu keywords")
        xhs_limit_count = 20  # Xiaohongshu limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < xhs_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = xhs_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[XiaoHongShuCrawler.search] Current search keyword: {keyword}")
            page = 1
            search_id = get_search_id()
            while (page - start_page + 1) * xhs_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Skip page {page}")
                    page += 1
                    continue

                try:
                    utils.logger.info(f"[XiaoHongShuCrawler.search] search Xiaohongshu keyword: {keyword}, page: {page}")
                    note_ids: List[str] = []
                    xsec_tokens: List[str] = []
                    notes_res = await self.xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        search_id=search_id,
                        page=page,
                        sort=(SearchSortType(config.SORT_TYPE) if config.SORT_TYPE != "" else SearchSortType.GENERAL),
                    )
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Search notes response: {notes_res}")
                    if not notes_res or not notes_res.get("has_more", False):
                        utils.logger.info("[XiaoHongShuCrawler.search] No more content!")
                        break
                    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                    task_list = [
                        self.get_note_detail_async_task(
                            note_id=post_item.get("id"),
                            xsec_source=post_item.get("xsec_source"),
                            xsec_token=post_item.get("xsec_token"),
                            semaphore=semaphore,
                        ) for post_item in notes_res.get("items", {}) if post_item.get("model_type") not in ("rec_query", "hot_query")
                    ]
                    note_details = await asyncio.gather(*task_list)
                    for note_detail in note_details:
                        if note_detail:
                            await xhs_store.update_xhs_note(note_detail)
                            await self.download_media(note_detail)
                            note_ids.append(note_detail.get("note_id"))
                            xsec_tokens.append(note_detail.get("xsec_token"))
                    page += 1
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Note details: {note_details}")
                    await self.batch_get_note_comments(note_ids, xsec_tokens)

                    # Sleep after each page navigation
                    await self._wait_between_requests(f"after search page {page - 1}")
                except DataFetchError:
                    utils.logger.error("[XiaoHongShuCrawler.search] Get note detail error")
                    break

    async def get_creators_and_notes(self) -> None:
        """Get creator's notes and retrieve their comment information."""
        utils.logger.info("[XiaoHongShuCrawler.get_creators_and_notes] Begin get Xiaohongshu creators")
        for creator_url in config.XHS_CREATOR_ID_LIST:
            try:
                # Parse creator URL to get user_id and security tokens
                creator_info: CreatorUrlInfo = parse_creator_info_from_url(creator_url)
                utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes] Parse creator URL info: {creator_info}")
                user_id = creator_info.user_id

                # get creator detail info from web html content
                createor_info: Dict = await self.xhs_client.get_creator_info(
                    user_id=user_id,
                    xsec_token=creator_info.xsec_token,
                    xsec_source=creator_info.xsec_source
                )
                if createor_info:
                    await xhs_store.save_creator(user_id, creator=createor_info)
            except ValueError as e:
                utils.logger.error(f"[XiaoHongShuCrawler.get_creators_and_notes] Failed to parse creator URL: {e}")
                continue
            except (IPBlockError, PlatformAccessError) as e:
                # Access restricted on the creator homepage, skip this creator instead of crashing the run.
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_creators_and_notes] Access restricted for creator {creator_url}: {e}. "
                    f"建议降低采集频率、更换 IP 或检查账号状态"
                )
                continue

            # Use fixed crawling interval
            crawl_interval = self._request_interval()
            # Get all note information of the creator
            all_notes_list = await self.xhs_client.get_all_notes_by_creator(
                user_id=user_id,
                crawl_interval=crawl_interval,
                callback=self.fetch_creator_notes_detail,
                xsec_token=creator_info.xsec_token,
                xsec_source=creator_info.xsec_source,
            )

            note_ids = []
            xsec_tokens = []
            for note_item in all_notes_list:
                note_ids.append(note_item.get("note_id"))
                xsec_tokens.append(note_item.get("xsec_token"))
            await self.batch_get_note_comments(note_ids, xsec_tokens)

    async def fetch_creator_notes_detail(self, note_list: List[Dict]):
        """Concurrently obtain the specified post list and save the data"""
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail_async_task(
                note_id=post_item.get("note_id"),
                xsec_source=post_item.get("xsec_source"),
                xsec_token=post_item.get("xsec_token"),
                semaphore=semaphore,
            ) for post_item in note_list
        ]

        note_details = await asyncio.gather(*task_list)
        for note_detail in note_details:
            if note_detail:
                await xhs_store.update_xhs_note(note_detail)
                await self.download_media(note_detail)

    async def get_specified_notes(self):
        """Get the information and comments of the specified post

        Note: Must specify note_id, xsec_source, xsec_token
        """
        get_note_detail_task_list = []
        for full_note_url in config.XHS_SPECIFIED_NOTE_URL_LIST:
            note_url_info: NoteUrlInfo = parse_note_info_from_note_url(full_note_url)
            utils.logger.info(f"[XiaoHongShuCrawler.get_specified_notes] Parse note url info: {note_url_info}")
            crawler_task = self.get_note_detail_async_task(
                note_id=note_url_info.note_id,
                xsec_source=note_url_info.xsec_source,
                xsec_token=note_url_info.xsec_token,
                semaphore=asyncio.Semaphore(config.MAX_CONCURRENCY_NUM),
            )
            get_note_detail_task_list.append(crawler_task)

        need_get_comment_note_ids = []
        xsec_tokens = []
        note_details = await asyncio.gather(*get_note_detail_task_list)
        for note_detail in note_details:
            if note_detail:
                need_get_comment_note_ids.append(note_detail.get("note_id", ""))
                xsec_tokens.append(note_detail.get("xsec_token", ""))
                await xhs_store.update_xhs_note(note_detail)
                await self.download_media(note_detail)
        await self.batch_get_note_comments(need_get_comment_note_ids, xsec_tokens)

    async def get_note_detail_async_task(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Dict]:
        """Get note detail

        Args:
            note_id:
            xsec_source:
            xsec_token:
            semaphore:

        Returns:
            Dict: note detail
        """
        note_detail = None
        utils.logger.info(f"[get_note_detail_async_task] Begin get note detail, note_id: {note_id}")
        async with semaphore:
            try:
                try:
                    note_detail = await self.xhs_client.get_note_by_id(note_id, xsec_source, xsec_token)
                except RetryError:
                    pass

                if not note_detail:
                    note_detail = await self.xhs_client.get_note_by_id_from_html(note_id, xsec_source, xsec_token,
                                                                                 enable_cookie=True)
                    if not note_detail:
                        utils.logger.warning(f"[skip] Failed to get note detail, Id: {note_id}, 跳过继续")
                        return None

                note_detail.update({"xsec_token": xsec_token, "xsec_source": xsec_source})

                # Sleep after fetching note detail
                await self._wait_between_requests(f"after note {note_id}")

                return note_detail

            except NoteNotFoundError as ex:
                utils.logger.warning(f"[XiaoHongShuCrawler.get_note_detail_async_task] Note not found: {note_id}, {ex}")
                return None
            except (IPBlockError, PlatformAccessError) as ex:
                # Access restricted (IP block / rate limit / account security).
                # Skip this note instead of aborting the whole asyncio.gather batch.
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_note_detail_async_task] Access restricted while getting note {note_id}: {ex}. "
                    f"建议降低采集频率、更换 IP 或检查账号状态"
                )
                return None
            except DataFetchError as ex:
                utils.logger.error(f"[XiaoHongShuCrawler.get_note_detail_async_task] Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[XiaoHongShuCrawler.get_note_detail_async_task] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, note_list: List[str], xsec_tokens: List[str]):
        """Batch get note comments"""
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[XiaoHongShuCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(f"[XiaoHongShuCrawler.batch_get_note_comments] Begin batch get note comments, note list: {note_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for index, note_id in enumerate(note_list):
            task = asyncio.create_task(
                self.get_comments(note_id=note_id, xsec_token=xsec_tokens[index], semaphore=semaphore),
                name=note_id,
            )
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, note_id: str, xsec_token: str, semaphore: asyncio.Semaphore):
        """Get note comments with keyword filtering and quantity limitation"""
        async with semaphore:
            utils.logger.info(f"[XiaoHongShuCrawler.get_comments] Begin get note id comments {note_id}")
            # Use fixed crawling interval
            crawl_interval = self._request_interval()
            await self.xhs_client.get_note_all_comments(
                note_id=note_id,
                xsec_token=xsec_token,
                crawl_interval=crawl_interval,
                callback=xhs_store.batch_update_xhs_note_comments,
                max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
            )

            # Sleep after fetching comments
            await self._wait_between_requests(f"after comments for note {note_id}")

    async def create_xhs_client(
        self, httpx_proxy: Optional[str], cookie_str: Optional[str] = None
    ) -> XiaoHongShuClient:
        """Create Xiaohongshu client"""
        utils.logger.info("[XiaoHongShuCrawler.create_xhs_client] Begin create Xiaohongshu API client ...")
        cookie_str = (cookie_str or resolve_xhs_cookies() or config.COOKIES).strip()
        cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
        xhs_client_obj = XiaoHongShuClient(
            proxy=httpx_proxy,
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "content-type": "application/json;charset=UTF-8",
                "origin": self.index_url,
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": f"{self.index_url}/",
                "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "Cookie": cookie_str,
            },
            playwright_page=None,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,  # Pass proxy pool for automatic refresh
            persist_cookies=True,
        )
        return xhs_client_obj

    async def launch_browser(self, *args, **kwargs):
        raise RuntimeError("XHS crawler uses pure API and does not launch a browser")

    async def download_media(self, note_detail: Dict) -> None:
        """下载笔记的媒体资源（封面、视频或图文图片）

        Args:
            note_detail: 笔记详情（原始 note_card 结构）
        """
        if not config.ENABLE_GET_MEDIA:
            return
        try:
            items = xhs_media.build_media_items(note_detail)
            if items:
                await self._get_media_downloader().download_all(items)
        except Exception as exc:
            # 媒体下载是旁路能力，解析异常/网络异常都不能中断爬取主流程
            utils.logger.error(f"[XiaoHongShuCrawler.download_media] 媒体下载异常: {exc}")

    def _get_media_downloader(self) -> MediaDownloader:
        """惰性创建媒体下载器，并同步最新的代理设置（代理池是就地刷新的）"""
        if self._media_downloader is None:
            self._media_downloader = MediaDownloader(
                platform="xhs",
                proxy=getattr(self.xhs_client, "proxy", None),
                extra_headers=self._media_headers(),
            )
        else:
            self._media_downloader.update_credentials(
                proxy=getattr(self.xhs_client, "proxy", None),
                extra_headers=self._media_headers(),
            )
        return self._media_downloader

    def _media_headers(self) -> Dict:
        """媒体请求头：平台 Referer（防盗链）+ UA"""
        return {
            "Referer": "https://www.xiaohongshu.com/",
            "User-Agent": self.user_agent,
        }
