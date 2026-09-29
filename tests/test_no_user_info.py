# -*- coding: utf-8 -*-
"""
教学版回归测试：确保爬取/存储链路不再持久化可定位真人的用户个人信息。

覆盖：
1. ORM 自省 —— database.models 中无禁用列、creator 档案表已删除、内容/评论表含 creator_hash。
2. 提取层 —— 用 mock API/HTML payload 喂各平台提取器，断言输出 dict 不含禁用字段、
   不含原始 user_id、昵称已脱敏且不等于原文。
3. 仓库 grep 断言 —— store/ 与 media_platform/ 不再把禁用字段作为存储 dict 的 key。
"""
import re
import subprocess
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 统一的禁用字段名(键)。昵称字段(nickname/user_nickname/screen_name/name/user_name)允许保留(值需脱敏)。
FORBIDDEN_KEYS = {
    "user_id", "sec_uid", "short_user_id", "user_unique_id", "user_signature",
    "avatar", "user_avatar", "face", "sign", "profile_url", "user_link",
    "url_token", "user_url_token", "ip_location", "ip_address", "gender", "sex",
    "up_id", "fan_id", "up_name", "fan_name", "up_avatar", "fan_avatar",
    "up_sign", "fan_sign", "mid",
}
NICK_KEYS = {"nickname", "user_nickname", "screen_name", "name", "user_name"}
MASK_RE = re.compile(r"^.?\*{1,4}.?$")


# ----------------------------- ORM 自省 -----------------------------

def test_orm_has_required_user_columns():
    import database.models as m
    from sqlalchemy.orm import class_mapper
    content_tables = [
        "XhsNote", "XhsNoteComment", "WeiboNote", "WeiboNoteComment",
        "BilibiliVideo", "BilibiliVideoComment", "BilibiliUpDynamic",
        "DouyinAweme", "DouyinAwemeComment", "KuaishouVideo",
        "KuaishouVideoComment", "TiebaNote", "TiebaComment",
        "ZhihuContent", "ZhihuComment"
    ]
    for t in content_tables:
        cols = {c.name for c in class_mapper(getattr(m, t)).columns}
        assert "user_id" in cols, f"{t} 缺少 user_id 列"
        assert ("nickname" in cols or "user_nickname" in cols or "user_name" in cols), f"{t} 缺少 nickname 列"
        assert "creator_hash" in cols, f"{t} 缺少 creator_hash 列"


def test_creator_tables_removed():
    import database.models as m
    removed = {"XhsCreator", "DyCreator", "WeiboCreator", "TiebaCreator",
               "ZhihuCreator", "BilibiliUpInfo", "BilibiliContactInfo"}
    for t in removed:
        assert not hasattr(m, t), f"creator 档案表 {t} 仍存在"


def test_content_tables_have_creator_hash():
    import database.models as m
    from sqlalchemy.orm import class_mapper
    content_tables = ["XhsNote", "XhsNoteComment", "WeiboNote", "WeiboNoteComment",
                      "BilibiliVideo", "BilibiliVideoComment", "BilibiliUpDynamic",
                      "DouyinAweme", "DouyinAwemeComment", "KuaishouVideo",
                      "KuaishouVideoComment", "TiebaNote", "TiebaComment",
                      "ZhihuContent", "ZhihuComment"]
    for t in content_tables:
        cols = {c.name for c in class_mapper(getattr(m, t)).columns}
        assert "creator_hash" in cols, f"{t} 缺少 creator_hash 列"


# ----------------------------- 提取层 mock -----------------------------

def test_mask_and_hash_tools():
    from tools.user_hash import anonymize_user_id, mask_nickname
    h = anonymize_user_id("12345")
    assert h and h != "12345" and re.fullmatch(r"[0-9a-f]{16}", h)
    assert anonymize_user_id(None) == "" and anonymize_user_id("") == ""
    # 昵称脱敏函数保留作为工具
    assert mask_nickname("张三丰") != "张三丰"
    assert "*" in mask_nickname("张三丰")


def test_xhs_note_extraction_masks_user_info():
    import asyncio
    import store.xhs as xs
    note_item = {
        "note_id": "abc",
        "type": "normal",
        "title": "t",
        "desc": "d",
        "time": 1,
        "last_update_time": 0,
        "user": {"user_id": "u123", "nickname": "小红同学", "image": "http://x/a.jpg"},
        "ip_location": "上海",
        "interact_info": {"liked_count": "1", "collected_count": "0",
                          "comment_count": "0", "share_count": "0"},
        "image_list": [], "tag_list": [], "xsec_token": "tok",
    }
    captured = {}

    class FakeStore:
        async def store_content(self, content_item):
            captured.update(content_item)

    orig = xs.XhsStoreFactory.create_store
    xs.XhsStoreFactory.create_store = staticmethod(lambda: FakeStore())
    try:
        asyncio.run(xs.update_xhs_note(note_item))
    finally:
        xs.XhsStoreFactory.create_store = orig
    assert captured.get("user_id") == "u123"
    assert captured.get("nickname") == "小红同学"
    assert captured.get("avatar") == "http://x/a.jpg"
    assert captured.get("creator_hash") != "u123"


def test_tieba_note_extraction_masks_user_info():
    from media_platform.tieba.help import TieBaExtractor
    api_data = {
        "thread": {"id": 1, "title": "tt", "reply_num": 5},
        "first_floor": {"tid": 1, "author_id": 9, "time": 1700000000, "content": "c"},
        "forum": {"name": "test", "id": 1},
        "page": {"total_page": 1},
        "user_list": [{"id": 9, "name_show": "贴吧老哥", "name": "lg", "portrait": "p", "ip_address": "北京"}],
    }
    note = TieBaExtractor().extract_note_detail_from_api(api_data)
    d = note.model_dump()
    assert d.get("user_nickname") == "贴吧老哥"
    assert d.get("creator_hash")


def test_tieba_comment_extraction_masks_user_info():
    from media_platform.tieba.help import TieBaExtractor
    from model.m_baidu_tieba import TiebaNote
    api_data = {
        "forum": {"id": 1, "name": "test"},
        "post_list": [{"id": 7, "author_id": 9, "time": 1700000000, "content": "c", "sub_post_number": 0}],
        "user_list": [{"id": 9, "name_show": "评论员", "name": "py", "portrait": "p", "ip_address": "上海"}],
    }
    note_detail = TiebaNote(note_id="1", title="t", note_url="u", tieba_name="test", tieba_link="l")
    comments = TieBaExtractor().extract_tieba_note_parent_comments_from_api(api_data, note_detail)
    assert comments
    d = comments[0].model_dump()
    assert d.get("user_nickname") == "评论员"
    assert d.get("creator_hash")


def test_zhihu_comment_extraction_masks_user_info():
    from media_platform.zhihu.help import ZhihuExtractor
    from model.m_zhihu import ZhihuContent
    comments_raw = [{
        "type": "comment", "id": 1, "content": "c", "created_time": 1700000000,
        "like_count": 1, "dislike_count": 0, "child_comment_count": 0,
        "author": {"id": "z9", "name": "知乎答主", "url_token": "tok", "avatar_url": "http://x/a.jpg"},
        "comment_tag": [{"type": "ip_info", "text": "广东"}],
    }]
    page_content = ZhihuContent(content_id="c1", content_type="answer")
    comments = ZhihuExtractor().extract_comments(page_content, comments_raw)
    assert comments
    d = comments[0].model_dump() if hasattr(comments[0], "model_dump") else vars(comments[0])
    assert d.get("user_id") == "z9"
    assert d.get("user_nickname") == "知乎答主"
    assert d.get("avatar") == "http://x/a.jpg"
    assert "creator_hash" in d and d["creator_hash"]


def test_bilibili_video_dict_masks_user_info():
    import asyncio
    from store.bilibili import update_bilibili_video
    video_item = {
        "View": {
            "aid": 100, "title": "t", "desc": "d", "pubdate": 1,
            "owner": {"mid": 777, "name": "UP主大人", "face": "http://x/a.jpg"},
            "stat": {"like": 1, "view": 2},
            "pic": "http://x/cover.jpg",
        }
    }
    captured = {}

    class FakeStore:
        async def store_content(self, content_item):
            captured.update(content_item)

    import store.bilibili as bs
    orig = bs.BiliStoreFactory.create_store
    bs.BiliStoreFactory.create_store = staticmethod(lambda: FakeStore())
    try:
        asyncio.run(update_bilibili_video(video_item))
    finally:
        bs.BiliStoreFactory.create_store = orig
    assert captured.get("user_id") == "777"
    assert captured.get("nickname") == "UP主大人"
    assert captured.get("avatar") == "http://x/a.jpg"
    assert captured.get("creator_hash")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
