# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

import sqlite3
from datetime import datetime

from fastapi.testclient import TestClient
from zoneinfo import ZoneInfo

from api.main import app
from api.sqlite_viewer import service as sqlite_viewer_service
from config import db_config


def _prepare_sqlite_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE douyin_aweme (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            sec_uid TEXT,
            short_user_id TEXT,
            user_unique_id TEXT,
            nickname TEXT,
            avatar TEXT,
            user_signature TEXT,
            ip_location TEXT,
            add_ts INTEGER,
            last_modify_ts INTEGER,
            aweme_id INTEGER,
            aweme_type TEXT,
            title TEXT,
            "desc" TEXT,
            create_time INTEGER,
            liked_count TEXT,
            comment_count TEXT,
            share_count TEXT,
            collected_count TEXT,
            aweme_url TEXT,
            cover_url TEXT,
            video_download_url TEXT,
            music_download_url TEXT,
            note_download_url TEXT,
            source_keyword TEXT
        );

        CREATE TABLE dy_creator (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            nickname TEXT,
            avatar TEXT,
            ip_location TEXT,
            add_ts INTEGER,
            last_modify_ts INTEGER,
            "desc" TEXT,
            gender TEXT,
            follows TEXT,
            fans TEXT,
            interaction TEXT,
            videos_count TEXT
        );

        CREATE TABLE weibo_creator (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            nickname TEXT,
            avatar TEXT,
            ip_location TEXT,
            add_ts INTEGER,
            last_modify_ts INTEGER,
            "desc" TEXT,
            gender TEXT,
            follows TEXT,
            fans TEXT,
            tag_list TEXT
        );
        """
    )

    conn.execute(
        """
        INSERT INTO douyin_aweme (
            id, user_id, nickname, avatar, add_ts, last_modify_ts, aweme_id, aweme_type,
            title, "desc", create_time, liked_count, comment_count, share_count,
            collected_count, aweme_url, source_keyword
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "sec_user_a",
            "创作者 A",
            "https://example.com/a.jpg",
            1771000000,
            1771001000,
            10001,
            "video",
            "较早的视频",
            "较早的视频描述",
            1771000000,
            "12",
            "3",
            "1",
            "2",
            "https://www.douyin.com/video/10001",
            "ai",
        ),
    )

    conn.execute(
        """
        INSERT INTO douyin_aweme (
            id, user_id, nickname, avatar, add_ts, last_modify_ts, aweme_id, aweme_type,
            title, "desc", create_time, liked_count, comment_count, share_count,
            collected_count, aweme_url, source_keyword
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            2,
            "sec_user_b",
            "创作者 B",
            "https://example.com/b.jpg",
            1774411200,
            1774412200,
            10002,
            "video",
            "一周内的视频",
            "一周内的视频描述",
            1774411200,
            "55",
            "8",
            "4",
            "9",
            "https://www.douyin.com/video/10002",
            "robot",
        ),
    )

    conn.execute(
        """
        INSERT INTO douyin_aweme (
            id, user_id, nickname, avatar, add_ts, last_modify_ts, aweme_id, aweme_type,
            title, "desc", create_time, liked_count, comment_count, share_count,
            collected_count, aweme_url, source_keyword
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            3,
            "sec_user_c",
            "创作者 C",
            "https://example.com/c.jpg",
            1774742400,
            1774743400,
            10003,
            "video",
            "今日的视频",
            "今日的视频描述",
            1774742400,
            "120",
            "25",
            "10",
            "17",
            "https://www.douyin.com/video/10003",
            "today",
        ),
    )

    conn.execute(
        """
        INSERT INTO dy_creator (
            id, user_id, nickname, avatar, ip_location, add_ts, last_modify_ts, "desc",
            gender, follows, fans, interaction, videos_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "MS4w-test-a",
            "抖音作者",
            "https://example.com/dy.jpg",
            "上海",
            1772100000,
            1773100000,
            "AIGC 创作者",
            "Male",
            "10",
            "999",
            "2000",
            "21",
        ),
    )

    conn.execute(
        """
        INSERT INTO weibo_creator (
            id, user_id, nickname, avatar, ip_location, add_ts, last_modify_ts, "desc",
            gender, follows, fans, tag_list
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "wb-user-1",
            "微博作者",
            "https://example.com/wb.jpg",
            "北京",
            1771100000,
            1771100000,
            "微博简介",
            "Female",
            "20",
            "555",
            "tech,ai",
        ),
    )

    conn.commit()
    conn.close()


def test_sqlite_viewer_page_available(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get("/sqlite-viewer")

    assert response.status_code == 200
    assert "SQLite 数据浏览器" in response.text


def _set_fixed_now(monkeypatch):
    monkeypatch.setattr(
        sqlite_viewer_service,
        "_now_in_shanghai",
        lambda: datetime(2026, 3, 29, 10, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )


def test_sqlite_viewer_options_returns_supported_platforms(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get("/api/sqlite-viewer/options")

    assert response.status_code == 200
    payload = response.json()

    assert [item["value"] for item in payload["platforms"]] == ["all", "xhs", "dy", "bili", "wb", "zhihu"]
    assert [item["value"] for item in payload["entity_types"]] == ["content", "comment", "creator"]
    assert payload["counts"]["dy"]["content"] == 3
    assert payload["counts"]["dy"]["creator"] == 1
    assert payload["counts"]["xhs"]["content"] == 0


def test_sqlite_viewer_list_orders_douyin_content_by_create_time_desc(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get("/api/sqlite-viewer/list", params={"platform": "dy", "entity_type": "content"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 3
    assert [item["source_id"] for item in payload["items"]] == ["10003", "10002", "10001"]
    assert payload["items"][0]["title"] == "今日的视频"


def test_sqlite_viewer_list_orders_all_creators_by_last_modify_ts_desc(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get("/api/sqlite-viewer/list", params={"platform": "all", "entity_type": "creator"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 2
    assert [item["platform"] for item in payload["items"]] == ["dy", "wb"]
    assert payload["items"][0]["author_name"] == "抖音作者"


def test_sqlite_viewer_filters_records_by_author_query(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get(
        "/api/sqlite-viewer/list",
        params={"platform": "dy", "entity_type": "content", "author_query": "创作者 B"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["author_query"] == "创作者 B"
    assert payload["total"] == 1
    assert [item["source_id"] for item in payload["items"]] == ["10002"]


def test_sqlite_viewer_filters_creators_by_author_query(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get(
        "/api/sqlite-viewer/list",
        params={"platform": "all", "entity_type": "creator", "author_query": "微博"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["author_query"] == "微博"
    assert payload["total"] == 1
    assert [item["platform"] for item in payload["items"]] == ["wb"]


def test_sqlite_viewer_filters_today_records_by_publish_time(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    _set_fixed_now(monkeypatch)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get(
        "/api/sqlite-viewer/list",
        params={"platform": "dy", "entity_type": "content", "time_filter": "today"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["source_id"] for item in payload["items"]] == ["10003"]


def test_sqlite_viewer_filters_last_week_records_by_publish_time(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    _set_fixed_now(monkeypatch)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get(
        "/api/sqlite-viewer/list",
        params={"platform": "dy", "entity_type": "content", "time_filter": "week"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [item["source_id"] for item in payload["items"]] == ["10003", "10002"]


def test_sqlite_viewer_filters_custom_date_range(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get(
        "/api/sqlite-viewer/list",
        params={
            "platform": "dy",
            "entity_type": "content",
            "time_filter": "custom",
            "start_date": "2026-03-24",
            "end_date": "2026-03-25",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["source_id"] for item in payload["items"]] == ["10002"]


def test_sqlite_viewer_returns_empty_list_for_missing_platform_table(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get("/api/sqlite-viewer/list", params={"platform": "xhs", "entity_type": "content"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["items"] == []


def test_sqlite_viewer_detail_returns_raw_record(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get("/api/sqlite-viewer/detail/content/dy/2")

    assert response.status_code == 200
    payload = response.json()

    assert payload["normalized"]["source_id"] == "10002"
    assert payload["raw"]["title"] == "一周内的视频"
    assert '"aweme_id": 10002' in payload["raw_json"]


def test_sqlite_viewer_rejects_invalid_filters(tmp_path, monkeypatch):
    db_path = tmp_path / "viewer.db"
    _prepare_sqlite_db(db_path)
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))

    client = TestClient(app)
    response = client.get("/api/sqlite-viewer/list", params={"platform": "ks", "entity_type": "content"})
    assert response.status_code == 400

    response = client.get("/api/sqlite-viewer/list", params={"platform": "dy", "entity_type": "dynamic"})
    assert response.status_code == 400

    response = client.get(
        "/api/sqlite-viewer/list",
        params={"platform": "dy", "entity_type": "content", "time_filter": "month"},
    )
    assert response.status_code == 400

    response = client.get(
        "/api/sqlite-viewer/list",
        params={"platform": "dy", "entity_type": "content", "time_filter": "custom"},
    )
    assert response.status_code == 400
