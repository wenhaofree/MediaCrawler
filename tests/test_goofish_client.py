# -*- coding: utf-8 -*-

import pytest

from media_platform.goofish.client import GooFishClient
from media_platform.goofish.help import GoofishExtractor


class FakePage:
    def __init__(self):
        self.url = "about:blank"
        self.payloads = []
        self.detail_calls = 0
        self.goto_count = 0
        self.wait_load_count = 0

    async def goto(self, url, wait_until=None):
        self.goto_count += 1
        self.url = url

    async def wait_for_load_state(self, state, timeout=None):
        self.wait_load_count += 1
        return None

    async def wait_for_timeout(self, timeout):
        return None

    async def evaluate(self, script, arg=None):
        payload = arg["payload"]
        self.payloads.append(payload)
        if payload["api"] == "mtop.taobao.idle.awesome.itemdetail":
            self.detail_calls += 1
            return {
                "ok": True,
                "response": {
                    "ret": ["SUCCESS::调用成功"],
                    "data": {
                        "itemDO": {
                            "price": "9.97",
                            "originPrice": "45",
                            "discountLabel": "2人小刀价",
                            "postage": "包邮",
                            "wantCnt": "3812",
                            "browseCnt": "2万浏览",
                        },
                        "sellerInfo": {
                            "userId": "2218417011733",
                            "sellerNick": "程序开发一人",
                            "lastActive": "10分钟前来过",
                            "joinTimeText": "来闲鱼2年",
                            "soldCountText": "卖出1878件宝贝",
                            "goodRateText": "好评率98%",
                        },
                        "html": '<a target="_blank" href="https://www.goofish.com/personal?userId=2218417011733"><img src="//img.alicdn.com/bao/avatar.webp" title="avatar"><div class="item-user-info-label--NLTMHARN">上海</div><div class="item-user-info-label--NLTMHARN">10分钟前来过</div></a>',
                    },
                },
            }
        if payload["api"] == "mtop.taobao.idle.pc.detail":
            self.detail_calls += 1
            return {
                "ok": True,
                "response": {
                    "ret": ["SUCCESS::调用成功"],
                    "data": {
                        "itemDO": {"publishTime": "1790553600000"},
                    },
                },
            }

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
                                "avatarUrl": "//img.example/avatar.jpg",
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
    assert item.user_id == "seller-1"
    assert item.user_nickname == "张三"
    assert item.user_avatar == "https://img.example/avatar.jpg"
    assert item.user_link == "https://www.goofish.com/personal?userId=seller-1"
    assert item.creator_hash


@pytest.mark.asyncio
async def test_goofish_search_reuses_one_page_for_keywords_and_pages():
    page = FakePage()
    client = GooFishClient(playwright_page=page)

    await client.search_items("耳机", page=2, page_size=30)
    await client.search_items("耳机", page=2, page_size=30)

    assert page.goto_count == 1
    assert page.wait_load_count == 1


@pytest.mark.asyncio
async def test_goofish_detail_enriches_want_browse_and_publish_time():
    page = FakePage()
    client = GooFishClient(playwright_page=page)

    item = await client.enrich_item_detail(
        GoofishExtractor.extract_item(
            {"data": {"id": "1001", "title": "降噪耳机"}}
        )
    )

    assert page.url == "about:blank"
    assert page.detail_calls == 2
    assert item.price == "9.97"
    assert item.original_price == "45"
    assert item.discount_label == "2人小刀价"
    assert item.shipping == "包邮"
    assert item.want_count == "3812人想要"
    assert item.browse_count == "2万浏览"
    assert item.publish_time == "2026-09-28 08:00:00"
    assert item.user_id == "2218417011733"
    assert item.user_nickname == "程序开发一人"
    assert item.user_avatar == "https://img.alicdn.com/bao/avatar.webp"
    assert item.user_link == "https://www.goofish.com/personal?userId=2218417011733"
    assert item.creator_hash and item.creator_hash != "2218417011733"
    assert item.seller_location == "上海"
    assert item.seller_last_active == "10分钟前来过"
    assert item.seller_join_time == "来闲鱼2年"
    assert item.seller_sold_count == "卖出1878件宝贝"
    assert item.seller_good_rate == "好评率98%"
