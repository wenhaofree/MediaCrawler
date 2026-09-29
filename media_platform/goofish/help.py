# -*- coding: utf-8 -*-

import re
from datetime import datetime
from typing import Any, Dict, Iterable, List

from model.m_goofish import GoofishItem
from tools.user_hash import anonymize_user_id


def _first(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, (int, float)):
            return str(value)
        text = str(value).strip()
        if text:
            return text
    return ""


def _dig(data: Dict, *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _price_text(value: Any) -> str:
    if isinstance(value, dict):
        value = _first(
            value.get("priceText"),
            value.get("text"),
            value.get("price"),
            value.get("value"),
            value.get("amount"),
            value.get("cent"),
        )
    text = _first(value)
    if not text:
        return ""
    match = re.search(r"(?:¥|￥)?\s*(\d+(?:\.\d+)?)", text)
    return match.group(1) if match else text


def _tag_text(value: Any) -> str:
    tags: List[str] = []

    def walk(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, str):
            text = item.strip()
            if text:
                tags.append(text)
            return
        if isinstance(item, list):
            for child in item:
                walk(child)
            return
        if isinstance(item, dict):
            for key in ("textContent", "gradientImageTextContent", "content", "text", "title", "label"):
                walk(item.get(key))
            for key in ("r1", "r2", "r3", "r4", "r5"):
                walk(item.get(key))

    walk(value)
    return " / ".join(dict.fromkeys(tags))


def _find_by_keys(value: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        for key in keys:
            if key in value and _first(value.get(key)):
                return value.get(key)
        for child in value.values():
            found = _find_by_keys(child, keys)
            if _first(found):
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_by_keys(child, keys)
            if _first(found):
                return found
    return ""


def _match_text(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.S)
    return match.group(1).strip() if match else ""


def _abs_url(url: str) -> str:
    url = _first(url)
    return f"https:{url}" if url.startswith("//") else url


class GoofishExtractor:
    @staticmethod
    def extract_detail_fields(detail: Dict) -> Dict[str, str]:
        text = str(detail)
        want = re.search(r"([\d.]+\s*万?\s*人想要)", text)
        browse = re.search(r"([\d.]+\s*万?\s*浏览)", text)
        publish = re.search(r"(?:发布于|发布时间|编辑于)\s*[:：]?\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?(?:\s+\d{1,2}:\d{2})?)", text)
        user_id = _first(_find_by_keys(detail, ("userId", "sellerId", "sellerUserId")))
        nickname = _first(_find_by_keys(detail, ("userNick", "sellerNick", "nick", "nickname")))
        user_link = _first(_find_by_keys(detail, ("userLink", "profileUrl", "userUrl"))) or _match_text(text, r'href=["\'](https://www\.goofish\.com/personal\?userId=[^"\']+)')
        user_avatar = _first(_find_by_keys(detail, ("avatar", "avatarUrl", "userAvatar", "headPicUrl"))) or _match_text(text, r'src=["\']((?://|https://)[^"\']+)["\'][^>]*title=["\']avatar')
        if not user_id:
            user_id = _match_text(user_link, r"userId=([^&]+)")
        return {
            "price": _price_text(_find_by_keys(detail, ("priceText", "currentPrice", "salePrice", "soldPrice", "price"))) or _match_text(text, r"[¥￥]\s*(?:<[^>]+>\s*)*([0-9]+(?:\.[0-9]+)?)"),
            "original_price": _price_text(_find_by_keys(detail, ("originalPrice", "originPrice", "oriPrice", "reservePrice"))) or _match_text(text, r"原价\s*[¥￥]?\s*([0-9]+(?:\.[0-9]+)?)"),
            "discount_label": _first(_find_by_keys(detail, ("discountLabel", "priceLabel", "fansPriceLabel"))) or _match_text(text, r"([0-9]+人小刀价|小刀价|可小刀)"),
            "shipping": _first(_find_by_keys(detail, ("shipping", "postage", "postFeeText", "freightText"))) or _match_text(text, r"(包邮|不包邮|邮费[^'\"<，。\\s]+)"),
            "want_count": want.group(1).replace(" ", "") if want else GoofishExtractor._find_count(detail, ("wantCnt", "wantCount", "wantNum"), "人想要"),
            "browse_count": browse.group(1).replace(" ", "") if browse else GoofishExtractor._find_count(detail, ("browseCnt", "browseCount", "viewCount", "pv"), "浏览"),
            "publish_time": publish.group(1) if publish else GoofishExtractor._find_publish_time(detail),
            "user_id": user_id,
            "user_nickname": nickname,
            "user_avatar": _abs_url(user_avatar),
            "user_link": user_link or (f"https://www.goofish.com/personal?userId={user_id}" if user_id else ""),
            "creator_hash": anonymize_user_id(user_id or nickname),
            "seller_location": _first(_find_by_keys(detail, ("sellerLocation", "sellerCity", "userCity", "cityName"))) or _match_text(text, r">([^<>]{1,20})</div>.{0,200}(?:[0-9]+分钟前来过|刚刚来过|今天来过|昨天来过)"),
            "seller_last_active": _first(_find_by_keys(detail, ("lastActive", "lastActiveTime", "lastVisitText"))) or _match_text(text, r"([0-9]+分钟前来过|刚刚来过|今天来过|昨天来过)"),
            "seller_join_time": _first(_find_by_keys(detail, ("joinTimeText", "registerTimeText"))) or _match_text(text, r"(来闲鱼[0-9]+[年月天])"),
            "seller_sold_count": _first(_find_by_keys(detail, ("soldCountText", "soldText"))) or _match_text(text, r"(卖出[0-9]+件宝贝)"),
            "seller_good_rate": _first(_find_by_keys(detail, ("goodRate", "goodRateText"))) or _match_text(text, r"(好评率[0-9.]+%)"),
        }

    @staticmethod
    def _find_publish_time(value: Any) -> str:
        if isinstance(value, dict):
            for key in ("publishTime", "publish_time", "gmtCreate", "createTime", "createdTime"):
                text = _first(value.get(key))
                if text:
                    return GoofishExtractor._format_time(text)
            for child in value.values():
                text = GoofishExtractor._find_publish_time(child)
                if text:
                    return text
        if isinstance(value, list):
            for child in value:
                text = GoofishExtractor._find_publish_time(child)
                if text:
                    return text
        return ""

    @staticmethod
    def _find_count(value: Any, keys: tuple[str, ...], suffix: str) -> str:
        if isinstance(value, dict):
            for key in keys:
                text = _first(value.get(key))
                if text:
                    return text if suffix in text else f"{text}{suffix}"
            for child in value.values():
                text = GoofishExtractor._find_count(child, keys, suffix)
                if text:
                    return text
        if isinstance(value, list):
            for child in value:
                text = GoofishExtractor._find_count(child, keys, suffix)
                if text:
                    return text
        return ""

    @staticmethod
    def _format_time(value: str) -> str:
        if value.isdigit() and len(value) >= 10:
            timestamp = int(value[:13]) / 1000 if len(value) >= 13 else int(value)
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        return value

    @staticmethod
    def extract_items(result_list: Iterable[Dict]) -> List[GoofishItem]:
        items: List[GoofishItem] = []
        for raw in result_list or []:
            item = GoofishExtractor.extract_item(raw)
            if item:
                items.append(item)
        return items

    @staticmethod
    def extract_item(raw: Dict) -> GoofishItem | None:
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        item = _dig(data, "item") or {}
        main = _dig(item, "main") or {}
        ex = _dig(main, "exContent") or _dig(item, "exContent") or _dig(data, "exContent") or {}
        click_param = _dig(main, "clickParam") or _dig(item, "clickParam") or {}
        click_args = _dig(click_param, "args") or {}

        item_id = _first(
            data.get("id"),
            item.get("itemId"),
            item.get("id"),
            ex.get("itemId"),
            ex.get("id"),
            main.get("itemId"),
            click_args.get("item_id"),
            click_args.get("itemId"),
        )
        if not item_id:
            return None

        category_id = _first(data.get("categoryId"), item.get("categoryId"), ex.get("categoryId"), click_args.get("cCatId"), "0")
        user_id = _first(
            data.get("userId"),
            data.get("sellerId"),
            item.get("userId"),
            item.get("sellerId"),
            ex.get("userId"),
            ex.get("sellerId"),
            main.get("userId"),
        )
        nickname = _first(
            data.get("userNick"),
            data.get("sellerNick"),
            item.get("userNick"),
            item.get("sellerNick"),
            item.get("nick"),
            ex.get("userNick"),
            ex.get("sellerNick"),
            main.get("userNick"),
        )

        return GoofishItem(
            item_id=item_id,
            title=_first(data.get("title"), item.get("title"), ex.get("title"), main.get("title")),
            desc=_first(
                _tag_text(data.get("fishTags") or ex.get("fishTags")),
                data.get("desc"),
                data.get("description"),
                data.get("city"),
                item.get("desc"),
                item.get("description"),
                ex.get("desc"),
                item.get("city"),
                ex.get("area"),
            ),
            item_url=f"https://www.goofish.com/item?id={item_id}&categoryId={category_id}",
            price=_price_text(data.get("priceText") or data.get("price") or item.get("priceText") or item.get("price") or ex.get("price") or ex.get("priceText")),
            original_price=_price_text(data.get("originalPrice") or data.get("originPrice") or item.get("originalPrice") or item.get("originPrice") or ex.get("originalPrice") or ex.get("originPrice")),
            discount_label=_first(data.get("discountLabel"), item.get("discountLabel"), ex.get("discountLabel")),
            shipping=_first(data.get("shipping"), data.get("postage"), item.get("shipping"), item.get("postage"), ex.get("shipping"), ex.get("postage")),
            area=_first(data.get("area"), data.get("city"), item.get("area"), item.get("city"), ex.get("area"), ex.get("city")),
            image_url=_first(data.get("picUrl"), data.get("image"), item.get("picUrl"), item.get("image"), ex.get("picUrl"), ex.get("mainPicUrl"), ex.get("picURL"), main.get("picUrl")),
            want_count=_first(data.get("wantCount"), data.get("wantNum"), item.get("wantCount"), item.get("wantNum"), ex.get("wantCount"), ex.get("wantNum")),
            user_id=user_id,
            user_nickname=nickname,
            user_avatar=_abs_url(_first(data.get("avatar"), data.get("avatarUrl"), data.get("userAvatar"), item.get("avatar"), item.get("avatarUrl"), ex.get("avatar"), ex.get("avatarUrl"))),
            user_link=_first(data.get("userLink"), data.get("profileUrl"), item.get("userLink"), item.get("profileUrl"), ex.get("userLink"), ex.get("profileUrl"), f"https://www.goofish.com/personal?userId={user_id}" if user_id else ""),
            creator_hash=anonymize_user_id(user_id or nickname),
            seller_location=_first(data.get("sellerLocation"), item.get("sellerLocation"), ex.get("sellerLocation")),
            seller_last_active=_first(data.get("lastActive"), item.get("lastActive"), ex.get("lastActive")),
            seller_join_time=_first(data.get("joinTimeText"), item.get("joinTimeText"), ex.get("joinTimeText")),
            seller_sold_count=_first(data.get("soldCountText"), item.get("soldCountText"), ex.get("soldCountText")),
            seller_good_rate=_first(data.get("goodRateText"), item.get("goodRateText"), ex.get("goodRateText")),
        )
