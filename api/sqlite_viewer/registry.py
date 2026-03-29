# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


SUPPORTED_PLATFORMS = ("xhs", "dy", "bili", "wb", "zhihu")
SUPPORTED_ENTITY_TYPES = ("content", "comment", "creator")

PLATFORM_LABELS: Dict[str, str] = {
    "all": "全部平台",
    "xhs": "小红书",
    "dy": "抖音",
    "bili": "Bilibili",
    "wb": "微博",
    "zhihu": "知乎",
}

ENTITY_TYPE_LABELS: Dict[str, str] = {
    "content": "内容",
    "comment": "评论",
    "creator": "创作者",
}


@dataclass(frozen=True)
class ViewerTableConfig:
    platform: str
    entity_type: str
    table_name: str
    pk_field: str
    source_id_expr: str
    title_expr: str
    summary_expr: str
    author_expr: str
    avatar_expr: str
    publish_raw_expr: str
    sort_ts_expr: str
    external_url_expr: str
    stats_json_expr: str
    raw_preview_expr: str


REGISTRY: Dict[str, Dict[str, ViewerTableConfig]] = {
    "xhs": {
        "content": ViewerTableConfig(
            platform="xhs",
            entity_type="content",
            table_name="xhs_note",
            pk_field="id",
            source_id_expr="note_id",
            title_expr="COALESCE(NULLIF(title, ''), NULLIF(\"desc\", ''), CAST(note_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(\"desc\", ''), NULLIF(title, ''), '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="time",
            sort_ts_expr="COALESCE(CAST(time AS INTEGER), 0)",
            external_url_expr="COALESCE(note_url, '')",
            stats_json_expr=(
                "json_object("
                "'liked_count', liked_count, "
                "'collected_count', collected_count, "
                "'comment_count', comment_count, "
                "'share_count', share_count)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(\"desc\", ''), NULLIF(title, ''), ''), 1, 140)",
        ),
        "comment": ViewerTableConfig(
            platform="xhs",
            entity_type="comment",
            table_name="xhs_note_comment",
            pk_field="id",
            source_id_expr="comment_id",
            title_expr="COALESCE(NULLIF(SUBSTR(content, 1, 60), ''), CAST(comment_id AS TEXT))",
            summary_expr="COALESCE(content, '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="create_time",
            sort_ts_expr="COALESCE(CAST(create_time AS INTEGER), 0)",
            external_url_expr="CASE WHEN note_id IS NOT NULL AND note_id != '' THEN printf('https://www.xiaohongshu.com/explore/%s', note_id) ELSE '' END",
            stats_json_expr=(
                "json_object("
                "'like_count', like_count, "
                "'sub_comment_count', sub_comment_count, "
                "'note_id', note_id)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(content, ''), 1, 140)",
        ),
        "creator": ViewerTableConfig(
            platform="xhs",
            entity_type="creator",
            table_name="xhs_creator",
            pk_field="id",
            source_id_expr="user_id",
            title_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(\"desc\", ''), '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="last_modify_ts",
            sort_ts_expr="COALESCE(CAST(last_modify_ts AS INTEGER), 0)",
            external_url_expr="CASE WHEN user_id IS NOT NULL AND user_id != '' THEN printf('https://www.xiaohongshu.com/user/profile/%s', user_id) ELSE '' END",
            stats_json_expr=(
                "json_object("
                "'fans', fans, "
                "'follows', follows, "
                "'interaction', interaction)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(\"desc\", ''), ''), 1, 140)",
        ),
    },
    "dy": {
        "content": ViewerTableConfig(
            platform="dy",
            entity_type="content",
            table_name="douyin_aweme",
            pk_field="id",
            source_id_expr="aweme_id",
            title_expr="COALESCE(NULLIF(title, ''), NULLIF(\"desc\", ''), CAST(aweme_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(\"desc\", ''), NULLIF(title, ''), '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="create_time",
            sort_ts_expr="COALESCE(CAST(create_time AS INTEGER), 0)",
            external_url_expr="COALESCE(aweme_url, '')",
            stats_json_expr=(
                "json_object("
                "'liked_count', liked_count, "
                "'comment_count', comment_count, "
                "'share_count', share_count, "
                "'collected_count', collected_count)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(\"desc\", ''), NULLIF(title, ''), ''), 1, 140)",
        ),
        "comment": ViewerTableConfig(
            platform="dy",
            entity_type="comment",
            table_name="douyin_aweme_comment",
            pk_field="id",
            source_id_expr="comment_id",
            title_expr="COALESCE(NULLIF(SUBSTR(content, 1, 60), ''), CAST(comment_id AS TEXT))",
            summary_expr="COALESCE(content, '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="create_time",
            sort_ts_expr="COALESCE(CAST(create_time AS INTEGER), 0)",
            external_url_expr="CASE WHEN aweme_id IS NOT NULL THEN printf('https://www.douyin.com/video/%s', aweme_id) ELSE '' END",
            stats_json_expr=(
                "json_object("
                "'like_count', like_count, "
                "'sub_comment_count', sub_comment_count, "
                "'aweme_id', aweme_id)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(content, ''), 1, 140)",
        ),
        "creator": ViewerTableConfig(
            platform="dy",
            entity_type="creator",
            table_name="dy_creator",
            pk_field="id",
            source_id_expr="user_id",
            title_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(\"desc\", ''), '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="last_modify_ts",
            sort_ts_expr="COALESCE(CAST(last_modify_ts AS INTEGER), 0)",
            external_url_expr="CASE WHEN user_id IS NOT NULL AND user_id != '' THEN printf('https://www.douyin.com/user/%s', user_id) ELSE '' END",
            stats_json_expr=(
                "json_object("
                "'fans', fans, "
                "'follows', follows, "
                "'interaction', interaction, "
                "'videos_count', videos_count)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(\"desc\", ''), ''), 1, 140)",
        ),
    },
    "bili": {
        "content": ViewerTableConfig(
            platform="bili",
            entity_type="content",
            table_name="bilibili_video",
            pk_field="id",
            source_id_expr="video_id",
            title_expr="COALESCE(NULLIF(title, ''), NULLIF(\"desc\", ''), CAST(video_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(\"desc\", ''), NULLIF(title, ''), '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="create_time",
            sort_ts_expr="COALESCE(CAST(create_time AS INTEGER), 0)",
            external_url_expr="COALESCE(video_url, '')",
            stats_json_expr=(
                "json_object("
                "'liked_count', liked_count, "
                "'video_play_count', video_play_count, "
                "'video_comment', video_comment, "
                "'video_share_count', video_share_count)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(\"desc\", ''), NULLIF(title, ''), ''), 1, 140)",
        ),
        "comment": ViewerTableConfig(
            platform="bili",
            entity_type="comment",
            table_name="bilibili_video_comment",
            pk_field="id",
            source_id_expr="comment_id",
            title_expr="COALESCE(NULLIF(SUBSTR(content, 1, 60), ''), CAST(comment_id AS TEXT))",
            summary_expr="COALESCE(content, '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="create_time",
            sort_ts_expr="COALESCE(CAST(create_time AS INTEGER), 0)",
            external_url_expr="CASE WHEN video_id IS NOT NULL THEN printf('https://www.bilibili.com/video/av%s', video_id) ELSE '' END",
            stats_json_expr=(
                "json_object("
                "'like_count', like_count, "
                "'sub_comment_count', sub_comment_count, "
                "'video_id', video_id)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(content, ''), 1, 140)",
        ),
        "creator": ViewerTableConfig(
            platform="bili",
            entity_type="creator",
            table_name="bilibili_up_info",
            pk_field="id",
            source_id_expr="user_id",
            title_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(sign, ''), '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="last_modify_ts",
            sort_ts_expr="COALESCE(CAST(last_modify_ts AS INTEGER), 0)",
            external_url_expr="CASE WHEN user_id IS NOT NULL THEN printf('https://space.bilibili.com/%s', user_id) ELSE '' END",
            stats_json_expr=(
                "json_object("
                "'total_fans', total_fans, "
                "'total_liked', total_liked, "
                "'user_rank', user_rank, "
                "'is_official', is_official)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(sign, ''), ''), 1, 140)",
        ),
    },
    "wb": {
        "content": ViewerTableConfig(
            platform="wb",
            entity_type="content",
            table_name="weibo_note",
            pk_field="id",
            source_id_expr="note_id",
            title_expr="COALESCE(NULLIF(SUBSTR(content, 1, 60), ''), CAST(note_id AS TEXT))",
            summary_expr="COALESCE(content, '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="create_time",
            sort_ts_expr="COALESCE(CAST(create_time AS INTEGER), 0)",
            external_url_expr="COALESCE(note_url, '')",
            stats_json_expr=(
                "json_object("
                "'liked_count', liked_count, "
                "'comments_count', comments_count, "
                "'shared_count', shared_count)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(content, ''), 1, 140)",
        ),
        "comment": ViewerTableConfig(
            platform="wb",
            entity_type="comment",
            table_name="weibo_note_comment",
            pk_field="id",
            source_id_expr="comment_id",
            title_expr="COALESCE(NULLIF(SUBSTR(content, 1, 60), ''), CAST(comment_id AS TEXT))",
            summary_expr="COALESCE(content, '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="create_time",
            sort_ts_expr="COALESCE(CAST(create_time AS INTEGER), 0)",
            external_url_expr="''",
            stats_json_expr=(
                "json_object("
                "'comment_like_count', comment_like_count, "
                "'sub_comment_count', sub_comment_count, "
                "'note_id', note_id)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(content, ''), 1, 140)",
        ),
        "creator": ViewerTableConfig(
            platform="wb",
            entity_type="creator",
            table_name="weibo_creator",
            pk_field="id",
            source_id_expr="user_id",
            title_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(\"desc\", ''), '')",
            author_expr="COALESCE(NULLIF(nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(avatar, '')",
            publish_raw_expr="last_modify_ts",
            sort_ts_expr="COALESCE(CAST(last_modify_ts AS INTEGER), 0)",
            external_url_expr="CASE WHEN user_id IS NOT NULL AND user_id != '' THEN printf('https://weibo.com/u/%s', user_id) ELSE '' END",
            stats_json_expr=(
                "json_object("
                "'fans', fans, "
                "'follows', follows)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(\"desc\", ''), ''), 1, 140)",
        ),
    },
    "zhihu": {
        "content": ViewerTableConfig(
            platform="zhihu",
            entity_type="content",
            table_name="zhihu_content",
            pk_field="id",
            source_id_expr="content_id",
            title_expr="COALESCE(NULLIF(title, ''), NULLIF(\"desc\", ''), CAST(content_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(\"desc\", ''), NULLIF(SUBSTR(content_text, 1, 140), ''), '')",
            author_expr="COALESCE(NULLIF(user_nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(user_avatar, '')",
            publish_raw_expr="created_time",
            sort_ts_expr="COALESCE(CAST(created_time AS INTEGER), 0)",
            external_url_expr="COALESCE(content_url, '')",
            stats_json_expr=(
                "json_object("
                "'voteup_count', voteup_count, "
                "'comment_count', comment_count, "
                "'content_type', content_type)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(content_text, ''), NULLIF(\"desc\", ''), ''), 1, 140)",
        ),
        "comment": ViewerTableConfig(
            platform="zhihu",
            entity_type="comment",
            table_name="zhihu_comment",
            pk_field="id",
            source_id_expr="comment_id",
            title_expr="COALESCE(NULLIF(SUBSTR(content, 1, 60), ''), CAST(comment_id AS TEXT))",
            summary_expr="COALESCE(content, '')",
            author_expr="COALESCE(NULLIF(user_nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(user_avatar, '')",
            publish_raw_expr="publish_time",
            sort_ts_expr="COALESCE(CAST(publish_time AS INTEGER), 0)",
            external_url_expr="''",
            stats_json_expr=(
                "json_object("
                "'like_count', like_count, "
                "'sub_comment_count', sub_comment_count, "
                "'content_id', content_id, "
                "'content_type', content_type)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(content, ''), 1, 140)",
        ),
        "creator": ViewerTableConfig(
            platform="zhihu",
            entity_type="creator",
            table_name="zhihu_creator",
            pk_field="id",
            source_id_expr="user_id",
            title_expr="COALESCE(NULLIF(user_nickname, ''), CAST(user_id AS TEXT))",
            summary_expr="COALESCE(NULLIF(url_token, ''), '')",
            author_expr="COALESCE(NULLIF(user_nickname, ''), CAST(user_id AS TEXT))",
            avatar_expr="COALESCE(user_avatar, '')",
            publish_raw_expr="last_modify_ts",
            sort_ts_expr="COALESCE(CAST(last_modify_ts AS INTEGER), 0)",
            external_url_expr="COALESCE(user_link, '')",
            stats_json_expr=(
                "json_object("
                "'fans', fans, "
                "'follows', follows, "
                "'answer_count', anwser_count, "
                "'article_count', article_count, "
                "'get_voteup_count', get_voteup_count)"
            ),
            raw_preview_expr="SUBSTR(COALESCE(NULLIF(url_token, ''), ''), 1, 140)",
        ),
    },
}


def validate_platform(platform: str) -> str:
    if platform != "all" and platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")
    return platform


def validate_entity_type(entity_type: str) -> str:
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    return entity_type


def get_config(platform: str, entity_type: str) -> ViewerTableConfig:
    validate_platform(platform)
    validate_entity_type(entity_type)
    if platform == "all":
        raise ValueError("Platform 'all' does not map to a single table")
    return REGISTRY[platform][entity_type]


def get_configs(platform: str, entity_type: str) -> List[ViewerTableConfig]:
    validate_platform(platform)
    validate_entity_type(entity_type)
    if platform == "all":
        return [REGISTRY[item][entity_type] for item in SUPPORTED_PLATFORMS]
    return [REGISTRY[platform][entity_type]]
