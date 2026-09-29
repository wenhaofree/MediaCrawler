# -*- coding: utf-8 -*-

from typing import Dict, List, Optional
from urllib.parse import quote

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from base.base_crawler import AbstractApiClient
from model.m_qimai import QimaiApp, QimaiComment
from tools import utils

from .help import QimaiExtractor


class QimaiClient(AbstractApiClient):
    def __init__(self, playwright_page: Page, headers: Optional[Dict[str, str]] = None):
        self.playwright_page = playwright_page
        self.headers = headers or {"User-Agent": utils.get_user_agent(), "Cookie": ""}
        self.cookie_urls = ["https://www.qimai.cn", "https://api.qimai.cn"]

    async def request(self, method, url, **kwargs):
        raise NotImplementedError("Qimai uses browser response interception to avoid analysis signing")

    async def update_cookies(self, browser_context: BrowserContext, urls: Optional[list[str]] = None):
        cookie_str, _ = await utils.convert_browser_context_cookies(
            browser_context,
            urls=urls or self.cookie_urls,
        )
        self.headers["Cookie"] = cookie_str

    async def search_apps(self, keyword: str) -> List[QimaiApp]:
        path = f"/search/index/country/cn/search/{quote(keyword)}"
        return await self._route_and_extract(path, "/search/index")

    async def get_app_detail(self, app_id: str) -> List[QimaiApp]:
        path = f"/app/baseinfo/appid/{quote(app_id)}/country/cn"
        payload = await self._route_and_payload(path, "/app/baseinfo")
        apps = QimaiExtractor.extract_apps(payload)
        await self._wait_detail_dom(app_id)
        detail_app = QimaiExtractor.app_from_detail_dom(await self._extract_detail_dom(app_id))
        if not detail_app or not any(
            [detail_app.category, detail_app.current_rank, detail_app.rating_value, detail_app.yesterday_downloads]
        ):
            utils.logger.warning(f"[QimaiClient.get_app_detail] detail DOM stale, fallback to goto: app_id={app_id}")
            old_page = self.playwright_page
            self.playwright_page = await old_page.context.new_page()
            await self.playwright_page.goto(f"https://www.qimai.cn{path}", wait_until="domcontentloaded")
            await self.playwright_page.wait_for_timeout(2000)
            try:
                await self.playwright_page.wait_for_selector(".app-info", timeout=10000)
            except Exception:
                pass
            await self._wait_detail_dom(app_id, timeout=10000)
            apps = []
            detail_app = QimaiExtractor.app_from_detail_dom(await self._extract_detail_dom(app_id))
        return QimaiExtractor.merge_apps(apps, detail_app)

    async def get_app_comments(self, app_id: str, max_count: int) -> List[QimaiComment]:
        path = f"/app/comment/appid/{quote(app_id)}/country/cn"
        payload = await self._route_and_payload(path, "/app/comment")
        comments = QimaiExtractor.comments_from_dom_rows(
            await self._extract_comment_rows(app_id, max_count),
            app_id,
        ) or QimaiExtractor.extract_comments(payload, app_id)
        if not comments or all(not comment.rating or not comment.create_time for comment in comments):
            await self.playwright_page.goto(f"https://www.qimai.cn{path}", wait_until="domcontentloaded")
            await self.playwright_page.wait_for_timeout(2000)
            comments = QimaiExtractor.comments_from_dom_rows(
                await self._extract_comment_rows(app_id, max_count),
                app_id,
            ) or comments
        seen = {comment.comment_id for comment in comments}
        while len(comments) < max_count:
            rows = await self._extract_comment_rows(app_id, max_count - len(comments))
            new_comments = [
                comment
                for comment in QimaiExtractor.comments_from_dom_rows(rows, app_id)
                if comment.comment_id not in seen
            ]
            comments.extend(new_comments)
            seen.update(comment.comment_id for comment in new_comments)
            if len(comments) >= max_count or not await self._next_comment_page():
                break
        return comments[:max_count]

    async def get_rank_apps(
        self,
        rank_type: str,
        rank_date: str,
        rank_genre: str,
        max_count: int = 0,
    ) -> List[QimaiApp]:
        url = f"https://www.qimai.cn/rank/index/brand/{quote(rank_type)}/genre/{quote(rank_genre)}/device/iphone/country/cn"
        if rank_date:
            url = f"{url}/date/{quote(rank_date)}"
        apps = self._mark_rank(await self._goto_and_extract(url, "/rank/index"), rank_type, rank_date, rank_genre)
        seen = {app.app_id for app in apps}
        while max_count <= 0 or len(apps) < max_count:
            payload = await self._scroll_for_payload("/rank/index")
            if not payload:
                break
            before = len(apps)
            for app in self._mark_rank(QimaiExtractor.extract_apps(payload), rank_type, rank_date, rank_genre):
                if app.app_id not in seen:
                    apps.append(app)
                    seen.add(app.app_id)
            if len(apps) == before:
                break
        return apps if max_count <= 0 else apps[:max_count]

    async def _goto_and_extract(self, url: str, api_path: str) -> List[QimaiApp]:
        return QimaiExtractor.extract_apps(await self._goto_and_payload(url, api_path))

    async def _route_and_extract(self, path: str, api_path: str) -> List[QimaiApp]:
        return QimaiExtractor.extract_apps(await self._route_and_payload(path, api_path))

    async def _route_and_payload(self, path: str, api_path: str) -> Dict:
        url = f"https://www.qimai.cn{path}"
        try:
            async with self.playwright_page.expect_response(
                lambda response: "api.qimai.cn" in response.url and api_path in response.url,
                timeout=15000,
            ) as response_info:
                await self._push_spa_route(path)
            return await (await response_info.value).json()
        except PlaywrightTimeoutError:
            utils.logger.warning(f"[QimaiClient._route_and_payload] SPA route timeout, fallback to goto: {url}")
            return await self._goto_and_payload(url, api_path)
        except Exception as exc:
            utils.logger.warning(f"[QimaiClient._route_and_payload] SPA route failed, fallback to goto: {url}, err={exc}")
            return await self._goto_and_payload(url, api_path)

    async def _push_spa_route(self, path: str) -> None:
        script = """async (path) => {
            const target = path.startsWith("http") ? path : `${location.origin}${path}`;
            const vue = document.querySelector("#app")?.__vue__;
            const router = vue && (vue.$router || vue.$root?.$router);
            if (router && router.push) {
                const pushed = router.push(target.replace(location.origin, ""));
                if (pushed && pushed.catch) await pushed.catch(() => {});
                return;
            }
            history.pushState({}, "", target);
            window.dispatchEvent(new PopStateEvent("popstate"));
        }"""
        await self.playwright_page.evaluate(script, path)

    async def _goto_and_payload(self, url: str, api_path: str) -> Dict:
        try:
            async with self.playwright_page.expect_response(
                lambda response: "api.qimai.cn" in response.url and api_path in response.url,
                timeout=15000,
            ) as response_info:
                await self.playwright_page.goto(url, wait_until="domcontentloaded")
            response = await response_info.value
            payload = await response.json()
        except PlaywrightTimeoutError:
            utils.logger.warning(f"[QimaiClient._goto_and_payload] timeout waiting for {api_path}: {url}")
            return {}
        except Exception as exc:
            utils.logger.warning(f"[QimaiClient._goto_and_payload] failed url={url}: {exc}")
            return {}
        return payload

    async def _scroll_for_payload(self, api_path: str) -> Dict:
        script = """() => {
            window.scrollTo(0, document.body.scrollHeight);
            for (const el of document.querySelectorAll("*")) {
                if (el.scrollHeight > el.clientHeight + 100) el.scrollTop = el.scrollHeight;
            }
        }"""
        try:
            async with self.playwright_page.expect_response(
                lambda response: "api.qimai.cn" in response.url and api_path in response.url,
                timeout=8000,
            ) as response_info:
                await self.playwright_page.evaluate(script)
            return await (await response_info.value).json()
        except PlaywrightTimeoutError:
            return {}
        except Exception as exc:
            utils.logger.warning(f"[QimaiClient._scroll_for_payload] failed api_path={api_path}: {exc}")
            return {}

    @staticmethod
    def _mark_rank(apps: List[QimaiApp], rank_type: str, rank_date: str, rank_genre: str) -> List[QimaiApp]:
        for app in apps:
            app.rank_type = rank_type
            app.rank_date = rank_date
            app.rank_genre = rank_genre
        return apps

    async def _extract_detail_dom(self, app_id: str) -> Dict:
        script = """(appId) => {
            const text = el => (el && el.innerText || "").replace(/\\s+/g, " ").trim();
            const label = el => {
                if (!el) return "";
                const clone = el.cloneNode(true);
                clone.querySelectorAll(".copy, i").forEach(child => child.remove());
                return text(clone);
            };
            const info = document.querySelector(".app-info");
            const data = { app_id: appId };
            const name = text(document.querySelector(".app-header .p-title"));
            if (name) data.app_name = name;
            if (!info) return data;
            for (const item of info.querySelectorAll(":scope > div")) {
                const type = label(item.querySelector(".type"));
                const value = text(item.querySelector(".value"));
                if (!type || !value) continue;
                const rating = item.querySelector(".value.rating input")?.value;
                data[type] = rating || value;
            }
            return data;
        }"""
        try:
            return await self.playwright_page.evaluate(script, app_id)
        except Exception as exc:
            utils.logger.warning(f"[QimaiClient._extract_detail_dom] failed app_id={app_id}: {exc}")
            return {"app_id": app_id}

    async def _wait_detail_dom(self, app_id: str, timeout: int = 5000) -> bool:
        try:
            await self.playwright_page.wait_for_function(
                """(appId) => {
                    const info = document.querySelector(".app-info");
                    return info && info.innerText.includes(appId) && info.innerText.includes("评分");
                }""",
                app_id,
                timeout=timeout,
            )
            return True
        except Exception:
            return False

    async def _extract_comment_rows(self, app_id: str, limit: int) -> List[Dict]:
        script = """({ appId, limit }) => {
            const text = el => (el && el.innerText || "").replace(/\\s+/g, " ").trim();
            return Array.from(document.querySelectorAll(".comment-details .ivu-table-body tbody tr"))
                .slice(0, limit)
                .map((row, index) => {
                    const deleted = row.querySelector(".comment-txt p.title i");
                    return {
                        app_id: appId,
                        rating: row.querySelector(".ivu-rate input")?.value || "",
                        title: text(row.querySelector(".comment-txt p.title > span:first-child")),
                        user_nickname: text(row.querySelector(".comment-txt .author a")),
                        content: text(row.querySelector('.comment-txt .body span[class^="comment-"]:not([class^="comment-dev-"])')),
                        create_time: text(row.querySelector("td:nth-child(3) span")),
                        developer_reply: text(row.querySelector(".developer-box .body")),
                        is_deleted: deleted && getComputedStyle(deleted).display !== "none" ? "1" : "0",
                        comment_id: `${appId}-${index}-${text(row.querySelector("td:nth-child(3) span"))}-${text(row.querySelector(".comment-txt p.title > span:first-child"))}`,
                    };
                });
        }"""
        try:
            return await self.playwright_page.evaluate(script, {"appId": app_id, "limit": limit})
        except Exception as exc:
            utils.logger.warning(f"[QimaiClient._extract_comment_rows] failed app_id={app_id}: {exc}")
            return []

    async def _next_comment_page(self) -> bool:
        next_page = self.playwright_page.locator(".comment-details .ivu-page-next:not(.ivu-page-disabled)").first
        if await next_page.count() == 0:
            return False
        await next_page.click()
        await self.playwright_page.wait_for_timeout(1200)
        return True
