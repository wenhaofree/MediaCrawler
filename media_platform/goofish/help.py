# -*- coding: utf-8 -*-

import re
from typing import Any, Dict, Iterable, List

from model.m_goofish import GoofishItem
from tools.user_hash import anonymize_user_id, mask_nickname


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


class GoofishExtractor:
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
            area=_first(data.get("area"), data.get("city"), item.get("area"), item.get("city"), ex.get("area"), ex.get("city")),
            image_url=_first(data.get("picUrl"), data.get("image"), item.get("picUrl"), item.get("image"), ex.get("picUrl"), ex.get("mainPicUrl"), ex.get("picURL"), main.get("picUrl")),
            want_count=_first(data.get("wantCount"), data.get("wantNum"), item.get("wantCount"), item.get("wantNum"), ex.get("wantCount"), ex.get("wantNum")),
            user_nickname=mask_nickname(nickname),
            creator_hash=anonymize_user_id(user_id or nickname),
        )
