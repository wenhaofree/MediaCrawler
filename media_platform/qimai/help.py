# -*- coding: utf-8 -*-

import hashlib
import re
from typing import Any, Dict, Iterable, List

from model.m_qimai import QimaiApp, QimaiComment
from tools.user_hash import anonymize_user_id, mask_nickname


class QimaiExtractor:
    APP_ID_KEYS = ("appid", "app_id", "appId")
    NAME_KEYS = ("appName", "app_name", "name", "title")

    @classmethod
    def extract_apps(cls, payload: Dict[str, Any]) -> List[QimaiApp]:
        apps: List[QimaiApp] = []
        seen: set[str] = set()
        for row in cls._walk_dicts(payload):
            app = cls._to_app(row)
            if app and app.app_id not in seen:
                apps.append(app)
                seen.add(app.app_id)
        return apps

    @classmethod
    def _walk_dicts(cls, value: Any) -> Iterable[Dict[str, Any]]:
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from cls._walk_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from cls._walk_dicts(child)

    @classmethod
    def _to_app(cls, row: Dict[str, Any]) -> QimaiApp | None:
        app_id = cls._pick(row, cls.APP_ID_KEYS)
        app_name = cls._pick(row, cls.NAME_KEYS)
        if not app_id or not app_name:
            return None
        return QimaiApp(
            app_id=app_id,
            app_name=app_name,
            subtitle=cls._pick(row, ("subtitle", "sub_title", "brief")),
            publisher=cls._pick(row, ("publisher", "developer", "author", "company", "sellerName")),
            category=cls._pick(row, ("category", "genre", "genreName", "class_name")),
            price=cls._pick(row, ("price", "priceText")),
            inner_purchase=cls._pick(row, ("inner_purchase", "inAppPurchase", "in_app_purchase")),
            current_rank=cls._pick(row, ("rank", "ranking", "current_rank")),
            rank_type=cls._pick(row, ("rank_type", "rankType")),
            rank_date=cls._pick(row, ("rank_date", "rankDate")),
            rank_genre=cls._pick(row, ("rank_genre", "rankGenre", "genre")),
            yesterday_downloads=cls._pick(row, ("yesterday_downloads", "yesterdayDownload", "download")),
            rating_value=cls._pick(row, ("rating", "rating_value", "averageUserRating")),
            rating_count=cls._pick(row, ("rating_count", "ratingCount", "userRatingCount")),
            icon_url=cls._pick(row, ("icon", "icon_url", "artworkUrl100", "logo")),
            bundle_id=cls._pick(row, ("bundleId", "bundle_id", "bundleid")),
            release_date=cls._pick(row, ("releaseDate", "release_date", "release_time")),
            last_update_date=cls._pick(row, ("last_update_date", "updated", "update_time")),
            version=cls._pick(row, ("version", "versionString")),
            app_desc=cls._pick(row, ("description", "app_desc", "desc")),
        )

    @classmethod
    def merge_apps(cls, apps: List[QimaiApp], extra: QimaiApp | None) -> List[QimaiApp]:
        if not extra:
            return apps
        for index, app in enumerate(apps):
            if app.app_id == extra.app_id:
                data = app.model_dump()
                data.update({key: value for key, value in extra.model_dump().items() if value})
                apps[index] = QimaiApp(**data)
                return apps
        return [extra]

    @classmethod
    def app_from_detail_dom(cls, row: Dict[str, Any]) -> QimaiApp | None:
        app_id = cls._pick(row, ("APP ID", "app_id"))
        if not app_id:
            return None
        rating_count = ""
        rating_value = ""
        for key, value in row.items():
            if "评分" in key:
                rating_count = "".join(re.findall(r"\d+", key))
                rating_value = str(value)
        return QimaiApp(
            app_id=app_id,
            app_name=cls._pick(row, ("app_name",)) or app_id,
            category=cls._pick(row, ("分类",)),
            price=cls._pick(row, ("价格",)),
            inner_purchase=cls._pick(row, ("内购",)),
            current_rank=cls._pick_rank(row),
            rating_value=rating_value,
            rating_count=rating_count,
            yesterday_downloads=cls._pick(row, ("昨日下载量",)),
            last_update_date=cls._pick(row, ("最近更新",)),
            release_date=cls._pick(row, ("最早发布",)),
        )

    @classmethod
    def extract_comments(cls, payload: Dict[str, Any], app_id: str) -> List[QimaiComment]:
        comments: List[QimaiComment] = []
        seen: set[str] = set()
        for row in cls._walk_dicts(payload):
            comment = cls._to_comment(row, app_id)
            if comment and comment.comment_id not in seen:
                comments.append(comment)
                seen.add(comment.comment_id)
        return comments

    @classmethod
    def comments_from_dom_rows(cls, rows: List[Dict[str, Any]], app_id: str) -> List[QimaiComment]:
        comments: List[QimaiComment] = []
        for row in rows:
            comment = cls._to_comment(row, app_id)
            if comment:
                comments.append(comment)
        return comments

    @classmethod
    def _to_comment(cls, row: Dict[str, Any], app_id: str) -> QimaiComment | None:
        title = cls._pick(row, ("title", "comment_title", "commentTitle"))
        content = cls._pick(row, ("content", "body", "comment", "commentContent"))
        create_time = cls._pick(row, ("create_time", "createTime", "created_at", "date", "time"))
        if not content:
            return None
        nickname = cls._pick(row, ("user_nickname", "nickname", "author", "userName"))
        raw_id = cls._pick(row, ("user_id", "userId", "author_id")) or nickname
        comment_id = cls._pick(row, ("comment_id", "commentId", "id")) or cls._comment_hash(
            app_id, title, content, create_time, raw_id
        )
        return QimaiComment(
            comment_id=comment_id,
            app_id=app_id,
            rating=cls._pick(row, ("rating", "star", "score")),
            title=title,
            content=content,
            user_nickname=mask_nickname(nickname),
            creator_hash=anonymize_user_id(raw_id),
            create_time=create_time,
            developer_reply=cls._pick(row, ("developer_reply", "reply")),
            is_deleted=cls._pick(row, ("is_deleted", "deleted")),
        )

    @staticmethod
    def _pick(row: Dict[str, Any], keys: Iterable[str]) -> str:
        for key in keys:
            value = row.get(key)
            if value is not None and value != "":
                return str(value)
        return ""

    @staticmethod
    def _pick_rank(row: Dict[str, Any]) -> str:
        for key, value in row.items():
            if "第" in str(value) and "名" in str(value):
                return str(value)
        return ""

    @staticmethod
    def _comment_hash(*parts: str) -> str:
        raw = "|".join(str(part) for part in parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
