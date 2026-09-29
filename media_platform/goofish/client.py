# -*- coding: utf-8 -*-

from typing import Dict, List, Optional
from urllib.parse import quote

from playwright.async_api import BrowserContext, Page

from base.base_crawler import AbstractApiClient
from model.m_goofish import GoofishItem
from tools import utils

from .help import GoofishExtractor


class GooFishClient(AbstractApiClient):
    def __init__(
        self,
        playwright_page: Page,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
    ):
        self.playwright_page = playwright_page
        self.headers = headers or {"User-Agent": utils.get_user_agent(), "Cookie": ""}
        self.timeout = timeout
        self._host = "https://www.goofish.com"
        self.cookie_urls = [self._host, "https://h5api.m.goofish.com"]
        self._search_page_ready = False

    async def request(self, method, url, **kwargs):
        raise NotImplementedError("Goofish MVP uses browser-side mtop requests only")

    async def update_cookies(self, browser_context: BrowserContext, urls: Optional[list[str]] = None):
        cookie_str, _ = await utils.convert_browser_context_cookies(
            browser_context,
            urls=urls or self.cookie_urls,
        )
        self.headers["Cookie"] = cookie_str
        utils.logger.info("[GooFishClient.update_cookies] Cookie has been updated")

    async def pong(self) -> bool:
        return True

    async def ensure_search_page(self, keyword: str) -> None:
        if self._search_page_ready:
            return
        if not self.playwright_page.url.startswith(f"{self._host}/search"):
            await self.playwright_page.goto(
                f"{self._host}/search?q={quote(keyword)}",
                wait_until="domcontentloaded",
            )
        try:
            await self.playwright_page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            await self.playwright_page.wait_for_timeout(1000)
        self._search_page_ready = True

    async def search_items(self, keyword: str, page: int, page_size: int = 30) -> List[GoofishItem]:
        await self.ensure_search_page(keyword)
        for api in (
            "mtop.taobao.idlemtopsearch.pc.search",
            "mtop.taobao.idle.web.item.search",
        ):
            response = await self._request_search_api(api, keyword, page, page_size)
            result_list = (response.get("data") or {}).get("resultList") or []
            items = GoofishExtractor.extract_items(result_list)
            if items:
                return items
            if result_list:
                utils.logger.warning(
                    f"[GooFishClient.search_items] {api} returned {len(result_list)} rows but extractor parsed 0 items"
                )
        return []

    async def enrich_item_detail(self, item: GoofishItem) -> GoofishItem:
        if not item.item_id:
            return item
        try:
            response = await self._request_detail_api(item.item_id, "mtop.taobao.idle.awesome.itemdetail")
            detail = GoofishExtractor.extract_detail_fields(response)
            if not detail["publish_time"]:
                pc_detail = GoofishExtractor.extract_detail_fields(
                    await self._request_detail_api(item.item_id, "mtop.taobao.idle.pc.detail")
                )
                detail = {key: detail[key] or pc_detail[key] for key in detail}
            for key, value in detail.items():
                if value:
                    setattr(item, key, value)
            if not item.seller_location:
                item.seller_location = item.area
        except Exception as exc:
            utils.logger.warning(f"[GooFishClient.enrich_item_detail] detail failed item_id={item.item_id}: {exc}")
        return item

    async def _request_detail_api(self, item_id: str, api: str) -> Dict:
        payload = {
            "api": api,
            "v": "1.0",
            "type": "POST",
            "dataType": "json",
            "needLoginPC": False,
            "showErrorToast": False,
            "data": {"itemId": item_id},
        }
        return await self._request_mtop_api(payload)

    async def _request_search_api(
        self,
        api: str,
        keyword: str,
        page: int,
        page_size: int,
    ) -> Dict:
        payload = {
            "api": api,
            "v": "1.0",
            "type": "POST",
            "dataType": "json",
            "needLoginPC": False,
            "showErrorToast": False,
            "data": {
                "pageNumber": page,
                "keyword": keyword,
                "fromFilter": False,
                "rowsPerPage": page_size,
                "sortValue": "",
                "sortField": "",
                "customDistance": "",
                "gps": "",
                "propValueStr": {},
                "customGps": "",
                "searchReqFromPage": "pcSearch",
            },
        }
        return await self._request_mtop_api(payload)

    async def _request_mtop_api(self, payload: Dict) -> Dict:
        api = payload.get("api", "")
        script = """async ({ payload, timeoutMs }) => {
                const waitForMtop = deadline => new Promise(resolve => {
                    const tick = () => {
                        if (window.lib && window.lib.mtop && window.lib.mtop.request) return resolve(true);
                        if (Date.now() > deadline) return resolve(false);
                        setTimeout(tick, 200);
                    };
                    tick();
                });
                if (!await waitForMtop(Date.now() + timeoutMs)) {
                    return { ok: false, message: "window.lib.mtop.request not loaded" };
                }
                try {
                    const response = await window.lib.mtop.request(payload);
                    return { ok: true, response };
                } catch (err) {
                    const message = err && (err.message || err.msg || err.ret || err.code || err.error);
                    return { ok: false, message: message ? String(message) : JSON.stringify(err || {}) };
                }
            }"""
        result = {}
        for attempt in range(2):
            try:
                result = await self.playwright_page.evaluate(
                    script,
                    {"payload": payload, "timeoutMs": self.timeout * 1000},
                )
                break
            except Exception as exc:
                if attempt == 1:
                    utils.logger.warning(f"[GooFishClient._request_mtop_api] {api} evaluate failed: {exc}")
                    return {}
                await self.playwright_page.wait_for_timeout(1000)
        if not result.get("ok"):
            utils.logger.warning(f"[GooFishClient._request_mtop_api] {api} failed: {result.get('message')}")
            return {}
        response = result.get("response") or {}
        ret = ",".join(response.get("ret") or [])
        if ret and not ret.startswith("SUCCESS"):
            utils.logger.warning(f"[GooFishClient._request_mtop_api] {api} ret: {ret}")
        return response
