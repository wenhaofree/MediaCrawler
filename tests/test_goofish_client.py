# -*- coding: utf-8 -*-

import pytest

from media_platform.goofish.client import GooFishClient


class FakePage:
    def __init__(self):
        self.url = "about:blank"
        self.payloads = []

    async def goto(self, url, wait_until=None):
        self.url = url

    async def evaluate(self, script, arg):
        payload = arg["payload"]
        self.payloads.append(payload)
        assert payload["data"]["keyword"] == "耳机"
        assert payload["data"]["pageNumber"] == 2
        assert payload["data"]["rowsPerPage"] == 30
        assert payload["data"]["searchReqFromPage"] == "pcSearch"

        if payload["api"] == "mtop.taobao.idlemtopsearch.pc.search":
            return {"ok": True, "response": {"ret": ["SUCCESS::调用成功"], "data": {"resultList": []}}}

        return {
            "ok": True,
            "response": {
                "ret": ["SUCCESS::调用成功"],
                "data": {
                    "resultList": [
                        {
                            "data": {
                                "id": "1001",
                                "categoryId": "500",
                                "title": "降噪耳机",
                                "price": {"priceText": "¥99"},
                                "city": "上海",
                                "picUrl": "https://img.example/1.jpg",
                                "sellerId": "seller-1",
                                "userNick": "张三",
                                "wantNum": "5人想要",
                                "item": {
                                    "main": {
                                        "exContent": {
                                            "fishTags": [{"r1": {"text": "包邮"}}],
                                        },
                                        "clickParam": {"args": {"item_id": "1001", "cCatId": "500"}},
                                    }
                                }
                            }
                        }
                    ]
                },
            },
        }


@pytest.mark.asyncio
async def test_goofish_search_uses_browser_mtop_and_parses_items():
    page = FakePage()
    client = GooFishClient(playwright_page=page)

    items = await client.search_items("耳机", page=2, page_size=30)

    assert page.url.startswith("https://www.goofish.com/search")
    assert [payload["api"] for payload in page.payloads] == [
        "mtop.taobao.idlemtopsearch.pc.search",
        "mtop.taobao.idle.web.item.search",
    ]
    assert len(items) == 1
    item = items[0]
    assert item.item_id == "1001"
    assert item.title == "降噪耳机"
    assert item.price == "99"
    assert item.area == "上海"
    assert item.desc == "包邮"
    assert item.item_url == "https://www.goofish.com/item?id=1001&categoryId=500"
    assert item.user_nickname == "张*"
    assert item.creator_hash
