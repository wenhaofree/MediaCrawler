# -*- coding: utf-8 -*-

from typing import Any, Dict, Iterable, List

from model.m_qimai import QimaiApp


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
            current_rank=cls._pick(row, ("rank", "ranking", "current_rank")),
            rating_value=cls._pick(row, ("rating", "rating_value", "averageUserRating")),
            rating_count=cls._pick(row, ("rating_count", "ratingCount", "userRatingCount")),
            icon_url=cls._pick(row, ("icon", "icon_url", "artworkUrl100", "logo")),
            bundle_id=cls._pick(row, ("bundleId", "bundle_id", "bundleid")),
            release_date=cls._pick(row, ("releaseDate", "release_date", "release_time")),
            last_update_date=cls._pick(row, ("last_update_date", "updated", "update_time")),
            version=cls._pick(row, ("version", "versionString")),
            app_desc=cls._pick(row, ("description", "app_desc", "desc")),
        )

    @staticmethod
    def _pick(row: Dict[str, Any], keys: Iterable[str]) -> str:
        for key in keys:
            value = row.get(key)
            if value is not None and value != "":
                return str(value)
        return ""
