# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/database/models.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。
#
# 教学版说明：为防止爬取到的用户个人信息被用于定位真人并私信骚扰，
# 本 ORM 不再持久化任何可识别用户的字段（用户 ID、IP 归属地、头像、
# 主页链接、签名、性别等一律不落库）。原始用户 ID 在提取层经
# tools.user_hash.anonymize_user_id 转为匿名 creator_hash 后写入，
# 仅用于"同一创作者"的内容分组；昵称保留但经 mask_nickname 中间脱敏。
# GoofishItem 是本地闲鱼采集例外，按用户配置保留卖家 ID、头像和主页链接。
# 创作者个人档案表（XhsCreator/DyCreator/WeiboCreator/TiebaCreator/
# ZhihuCreator/BilibiliUpInfo/BilibiliContactInfo）已整体移除。

from sqlalchemy import create_engine, Column, Integer, Text, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class BilibiliVideo(Base):
    __tablename__ = 'bilibili_video'
    id = Column(Integer, primary_key=True, comment='主键ID')
    video_id = Column(String(64), nullable=False, index=True, unique=True, comment='视频ID')
    video_url = Column(Text, nullable=False, comment='视频URL')
    user_id = Column(String(64), index=True, comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    liked_count = Column(Integer, comment='点赞数')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    video_type = Column(Text, comment='视频类型')
    title = Column(Text, comment='视频标题')
    desc = Column(Text, comment='视频描述')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    disliked_count = Column(Text, comment='点踩数')
    video_play_count = Column(Text, comment='播放数')
    video_favorite_count = Column(Text, comment='收藏数')
    video_share_count = Column(Text, comment='分享数')
    video_coin_count = Column(Text, comment='硬币数')
    video_danmaku = Column(Text, comment='弹幕数')
    video_comment = Column(Text, comment='评论数')
    video_cover_url = Column(Text, comment='视频封面URL')
    source_keyword = Column(Text, default='', comment='来源关键词')

class BilibiliVideoComment(Base):
    __tablename__ = 'bilibili_video_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(64), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    sex = Column(Text, comment='性别')
    sign = Column(Text, comment='签名')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(String(128), index=True, comment='评论ID')
    video_id = Column(String(64), index=True, comment='视频ID')
    content = Column(Text, comment='评论内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    sub_comment_count = Column(Text, comment='子评论数')
    parent_comment_id = Column(String(255), comment='父评论ID')
    like_count = Column(Text, default='0', comment='点赞数')

class BilibiliUpDynamic(Base):
    __tablename__ = 'bilibili_up_dynamic'
    id = Column(Integer, primary_key=True, comment='主键ID')
    dynamic_id = Column(String(128), index=True, comment='动态ID')
    user_id = Column(String(64), comment='用户ID')
    user_name = Column(Text, comment='用户名称')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    text = Column(Text, comment='动态内容')
    type = Column(Text, comment='动态类型')
    pub_ts = Column(BigInteger, comment='发布时间戳')
    total_comments = Column(Integer, comment='总评论数')
    total_forwards = Column(Integer, comment='总转发数')
    total_liked = Column(Integer, comment='总点赞数')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class DouyinAweme(Base):
    __tablename__ = 'douyin_aweme'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    sec_uid = Column(String(255), comment='安全用户ID')
    short_user_id = Column(String(255), comment='短用户ID')
    user_unique_id = Column(String(255), comment='用户唯一ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    user_signature = Column(Text, comment='用户签名')
    ip_location = Column(Text, comment='IP地址位置')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    aweme_id = Column(String(255), index=True, comment='作品ID')
    aweme_type = Column(Text, comment='作品类型')
    title = Column(Text, comment='作品标题')
    desc = Column(Text, comment='作品描述')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    liked_count = Column(Text, comment='点赞数')
    comment_count = Column(Text, comment='评论数')
    share_count = Column(Text, comment='分享数')
    collected_count = Column(Text, comment='收藏数')
    aweme_url = Column(Text, comment='作品URL')
    cover_url = Column(Text, comment='封面URL')
    video_download_url = Column(Text, comment='视频下载URL')
    music_download_url = Column(Text, comment='音乐下载URL')
    note_download_url = Column(Text, comment='笔记下载URL')
    source_keyword = Column(Text, default='', comment='来源关键词')

class DouyinAwemeComment(Base):
    __tablename__ = 'douyin_aweme_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    sec_uid = Column(String(255), comment='安全用户ID')
    short_user_id = Column(String(255), comment='短用户ID')
    user_unique_id = Column(String(255), comment='用户唯一ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    user_signature = Column(Text, comment='用户签名')
    ip_location = Column(Text, comment='IP地址位置')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(String(255), index=True, comment='评论ID')
    aweme_id = Column(String(255), index=True, comment='作品ID')
    content = Column(Text, comment='评论内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    sub_comment_count = Column(Text, comment='子评论数')
    parent_comment_id = Column(String(255), comment='父评论ID')
    like_count = Column(Text, default='0', comment='点赞数')
    pictures = Column(Text, default='', comment='图片')

class KuaishouVideo(Base):
    __tablename__ = 'kuaishou_video'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(64), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    video_id = Column(String(255), index=True, comment='视频ID')
    video_type = Column(Text, comment='视频类型')
    title = Column(Text, comment='视频标题')
    desc = Column(Text, comment='视频描述')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    liked_count = Column(Text, comment='点赞数')
    viewd_count = Column(Text, comment='观看数')
    video_url = Column(Text, comment='视频URL')
    video_cover_url = Column(Text, comment='视频封面URL')
    video_play_url = Column(Text, comment='视频播放URL')
    source_keyword = Column(Text, default='', comment='来源关键词')

class KuaishouVideoComment(Base):
    __tablename__ = 'kuaishou_video_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(Text, comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(String(255), index=True, comment='评论ID')
    video_id = Column(String(255), index=True, comment='视频ID')
    content = Column(Text, comment='评论内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    sub_comment_count = Column(Text, comment='子评论数')

class GoofishItem(Base):
    __tablename__ = 'goofish_item'
    id = Column(Integer, primary_key=True, comment='主键ID')
    item_id = Column(String(128), nullable=False, index=True, unique=True, comment='商品ID')
    title = Column(Text, comment='商品标题')
    desc = Column(Text, comment='商品描述')
    item_url = Column(Text, comment='商品URL')
    price = Column(Text, comment='价格')
    original_price = Column(Text, comment='原价')
    discount_label = Column(Text, comment='价格标签')
    shipping = Column(Text, comment='邮费')
    area = Column(Text, comment='地区')
    image_url = Column(Text, comment='主图URL')
    want_count = Column(Text, comment='想要人数')
    browse_count = Column(Text, comment='浏览量')
    publish_time = Column(Text, comment='发布时间')
    user_id = Column(Text, comment='卖家ID')
    user_nickname = Column(Text, comment='卖家昵称')
    user_avatar = Column(Text, comment='卖家头像')
    user_link = Column(Text, comment='卖家主页')
    creator_hash = Column(String(64), index=True, comment='卖家匿名哈希')
    seller_location = Column(Text, comment='卖家地区')
    seller_last_active = Column(Text, comment='卖家最近活跃')
    seller_join_time = Column(Text, comment='卖家闲鱼年限')
    seller_sold_count = Column(Text, comment='卖家卖出数')
    seller_good_rate = Column(Text, comment='卖家好评率')
    source_keyword = Column(Text, default='', comment='来源关键词')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class QimaiApp(Base):
    __tablename__ = 'qimai_app'
    id = Column(Integer, primary_key=True, comment='主键ID')
    app_id = Column(String(128), nullable=False, index=True, unique=True, comment='应用ID')
    app_name = Column(Text, comment='应用名称')
    subtitle = Column(Text, comment='副标题')
    publisher = Column(Text, comment='开发者')
    category = Column(Text, comment='分类')
    current_rank = Column(Text, comment='当前排名')
    rating_value = Column(Text, comment='评分')
    rating_count = Column(Text, comment='评分人数')
    icon_url = Column(Text, comment='图标URL')
    bundle_id = Column(Text, comment='包名')
    release_date = Column(Text, comment='发布日期')
    last_update_date = Column(Text, comment='最近更新日期')
    version = Column(Text, comment='版本')
    app_desc = Column(Text, comment='应用描述')
    source_keyword = Column(Text, default='', comment='来源关键词')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class WeiboNote(Base):
    __tablename__ = 'weibo_note'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    gender = Column(Text, comment='性别')
    profile_url = Column(Text, comment='个人主页URL')
    ip_location = Column(Text, default='', comment='IP地址位置')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    note_id = Column(String(64), index=True, comment='笔记ID')
    content = Column(Text, comment='笔记内容')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    create_date_time = Column(String(255), index=True, comment='创建日期时间')
    liked_count = Column(Text, comment='点赞数')
    comments_count = Column(Text, comment='评论数')
    shared_count = Column(Text, comment='分享数')
    note_url = Column(Text, comment='笔记URL')
    source_keyword = Column(Text, default='', comment='来源关键词')

class WeiboNoteComment(Base):
    __tablename__ = 'weibo_note_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    gender = Column(Text, comment='性别')
    profile_url = Column(Text, comment='个人主页URL')
    ip_location = Column(Text, default='', comment='IP地址位置')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(String(64), index=True, comment='评论ID')
    note_id = Column(String(64), index=True, comment='笔记ID')
    content = Column(Text, comment='评论内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    create_date_time = Column(String(255), index=True, comment='创建日期时间')
    comment_like_count = Column(Text, comment='评论点赞数')
    sub_comment_count = Column(Text, comment='子评论数')
    parent_comment_id = Column(String(255), comment='父评论ID')

class XhsNote(Base):
    __tablename__ = 'xhs_note'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    note_id = Column(String(255), index=True, comment='笔记ID')
    type = Column(Text, comment='笔记类型')
    title = Column(Text, comment='笔记标题')
    desc = Column(Text, comment='笔记描述')
    video_url = Column(Text, comment='视频URL')
    time = Column(BigInteger, index=True, comment='时间戳')
    last_update_time = Column(BigInteger, comment='最后更新时间戳')
    liked_count = Column(Text, comment='点赞数')
    collected_count = Column(Text, comment='收藏数')
    comment_count = Column(Text, comment='评论数')
    share_count = Column(Text, comment='分享数')
    image_list = Column(Text, comment='图片列表')
    tag_list = Column(Text, comment='标签列表')
    note_url = Column(Text, comment='笔记URL')
    source_keyword = Column(Text, default='', comment='来源关键词')
    xsec_token = Column(Text, comment='Xsec Token')

class XhsNoteComment(Base):
    __tablename__ = 'xhs_note_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(String(255), index=True, comment='评论ID')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    note_id = Column(String(255), comment='笔记ID')
    content = Column(Text, comment='评论内容')
    sub_comment_count = Column(Integer, comment='子评论数')
    pictures = Column(Text, comment='图片')
    parent_comment_id = Column(String(255), comment='父评论ID')
    like_count = Column(Text, comment='点赞数')

class TiebaNote(Base):
    __tablename__ = 'tieba_note'
    id = Column(Integer, primary_key=True, comment='主键ID')
    note_id = Column(String(644), index=True, comment='笔记ID')
    title = Column(Text, comment='笔记标题')
    desc = Column(Text, comment='笔记描述')
    note_url = Column(Text, comment='笔记URL')
    publish_time = Column(String(255), index=True, comment='发布时间')
    user_id = Column(String(64), default='', comment='用户ID')
    user_link = Column(Text, default='', comment='用户链接')
    user_nickname = Column(Text, default='', comment='用户昵称')
    nickname = Column(Text, default='', comment='用户昵称')
    user_avatar = Column(Text, default='', comment='用户头像')
    avatar = Column(Text, default='', comment='用户头像')
    tieba_id = Column(String(255), default='', comment='贴吧ID')
    tieba_name = Column(Text, comment='贴吧名称')
    tieba_link = Column(Text, comment='贴吧链接')
    total_replay_num = Column(Integer, default=0, comment='总回复数')
    total_replay_page = Column(Integer, default=0, comment='总回复页数')
    ip_location = Column(Text, default='', comment='IP地址位置')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    source_keyword = Column(Text, default='', comment='来源关键词')

class TiebaComment(Base):
    __tablename__ = 'tieba_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    comment_id = Column(String(255), index=True, comment='评论ID')
    parent_comment_id = Column(String(255), default='', comment='父评论ID')
    content = Column(Text, comment='评论内容')
    user_id = Column(String(64), default='', comment='用户ID')
    user_link = Column(Text, default='', comment='用户链接')
    user_nickname = Column(Text, default='', comment='用户昵称')
    nickname = Column(Text, default='', comment='用户昵称')
    user_avatar = Column(Text, default='', comment='用户头像')
    avatar = Column(Text, default='', comment='用户头像')
    tieba_id = Column(String(255), default='', comment='贴吧ID')
    tieba_name = Column(Text, comment='贴吧名称')
    tieba_link = Column(Text, comment='贴吧链接')
    publish_time = Column(String(255), index=True, comment='发布时间')
    ip_location = Column(Text, default='', comment='IP地址位置')
    sub_comment_count = Column(Integer, default=0, comment='子评论数')
    note_id = Column(String(255), index=True, comment='笔记ID')
    note_url = Column(Text, comment='笔记URL')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class ZhihuContent(Base):
    __tablename__ = 'zhihu_content'
    id = Column(Integer, primary_key=True, comment='主键ID')
    content_id = Column(String(64), index=True, comment='内容ID')
    content_type = Column(Text, comment='内容类型')
    content_text = Column(Text, comment='内容文本')
    content_url = Column(Text, comment='内容URL')
    question_id = Column(String(255), comment='问题ID')
    title = Column(Text, comment='标题')
    desc = Column(Text, comment='描述')
    created_time = Column(String(32), index=True, comment='创建时间')
    updated_time = Column(Text, comment='更新时间')
    voteup_count = Column(Integer, default=0, comment='赞同数')
    comment_count = Column(Integer, default=0, comment='评论数')
    source_keyword = Column(Text, comment='来源关键词')
    user_id = Column(String(255), comment='用户ID')
    user_link = Column(Text, comment='用户链接')
    user_nickname = Column(Text, comment='用户昵称')
    nickname = Column(Text, comment='用户昵称')
    user_avatar = Column(Text, comment='用户头像')
    avatar = Column(Text, comment='用户头像')
    user_url_token = Column(Text, comment='用户URL Token')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class ZhihuComment(Base):
    __tablename__ = 'zhihu_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    comment_id = Column(String(64), index=True, comment='评论ID')
    parent_comment_id = Column(String(64), comment='父评论ID')
    content = Column(Text, comment='评论内容')
    publish_time = Column(String(32), index=True, comment='发布时间')
    ip_location = Column(Text, comment='IP地址位置')
    sub_comment_count = Column(Integer, default=0, comment='子评论数')
    like_count = Column(Integer, default=0, comment='点赞数')
    dislike_count = Column(Integer, default=0, comment='点踩数')
    content_id = Column(String(64), index=True, comment='内容ID')
    content_type = Column(Text, comment='内容类型')
    user_id = Column(String(64), comment='用户ID')
    user_link = Column(Text, comment='用户链接')
    user_nickname = Column(Text, comment='用户昵称')
    nickname = Column(Text, comment='用户昵称')
    user_avatar = Column(Text, comment='用户头像')
    avatar = Column(Text, comment='用户头像')
    creator_hash = Column(String(64), index=True, comment='创作者匿名哈希')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')


class ScheduledCrawlTask(Base):
    __tablename__ = 'scheduled_crawl_task'
    id = Column(Integer, primary_key=True, comment='主键ID')
    name = Column(Text, nullable=False, comment='任务名称')
    platform = Column(String(32), nullable=False, index=True, comment='平台')
    run_time = Column(String(8), nullable=False, comment='每日执行时间 HH:MM')
    max_pages = Column(Integer, nullable=False, default=3, comment='每个作者的最大采集页数')
    enable_comments = Column(Integer, nullable=False, default=0, comment='是否采集评论')
    enable_sub_comments = Column(Integer, nullable=False, default=0, comment='是否采集二级评论')
    save_option = Column(String(32), nullable=False, default='sqlite', comment='保存方式')
    status = Column(String(16), nullable=False, default='active', index=True, comment='任务状态')
    last_run_at = Column(Text, comment='最近执行时间')
    last_success_at = Column(Text, comment='最近成功时间')
    last_error = Column(Text, comment='最近错误')
    next_run_at = Column(Text, comment='下次执行时间')
    created_at = Column(Text, nullable=False, comment='创建时间')
    updated_at = Column(Text, nullable=False, comment='更新时间')


class ScheduledCrawlTaskCreator(Base):
    __tablename__ = 'scheduled_crawl_task_creator'
    id = Column(Integer, primary_key=True, comment='主键ID')
    task_id = Column(Integer, nullable=False, index=True, comment='任务ID')
    sort_order = Column(Integer, nullable=False, default=0, comment='排序')
    raw_input = Column(Text, nullable=False, comment='原始作者输入')
    normalized_creator_id = Column(Text, nullable=False, comment='标准化作者ID')
    display_name = Column(Text, comment='显示名称')
    xhs_user_id = Column(Text, comment='小红书用户ID')
    xhs_xsec_token = Column(Text, comment='小红书最近成功token')
    xhs_xsec_source = Column(Text, comment='小红书最近成功source')
    last_success_at = Column(Text, comment='最近成功时间')
    last_error = Column(Text, comment='最近错误')
    created_at = Column(Text, nullable=False, comment='创建时间')
    updated_at = Column(Text, nullable=False, comment='更新时间')


class ScheduledCrawlRun(Base):
    __tablename__ = 'scheduled_crawl_run'
    id = Column(Integer, primary_key=True, comment='主键ID')
    task_id = Column(Integer, nullable=False, index=True, comment='任务ID')
    status = Column(String(16), nullable=False, index=True, comment='执行状态')
    trigger_type = Column(String(16), nullable=False, default='schedule', comment='触发方式')
    started_at = Column(Text, nullable=False, comment='开始时间')
    finished_at = Column(Text, comment='结束时间')
    error_message = Column(Text, comment='错误信息')
    created_at = Column(Text, nullable=False, comment='创建时间')


class ScheduledCrawlRunItem(Base):
    __tablename__ = 'scheduled_crawl_run_item'
    id = Column(Integer, primary_key=True, comment='主键ID')
    run_id = Column(Integer, nullable=False, index=True, comment='运行ID')
    task_id = Column(Integer, nullable=False, index=True, comment='任务ID')
    creator_id = Column(Integer, nullable=False, index=True, comment='作者配置ID')
    raw_input = Column(Text, nullable=False, comment='原始作者输入')
    normalized_creator_id = Column(Text, nullable=False, comment='标准化作者ID')
    status = Column(String(16), nullable=False, index=True, comment='执行状态')
    started_at = Column(Text, nullable=False, comment='开始时间')
    finished_at = Column(Text, comment='结束时间')
    pages_fetched = Column(Integer, default=0, comment='采集页数')
    items_fetched = Column(Integer, default=0, comment='新增条数')
    error_message = Column(Text, comment='错误信息')
    effective_creator_arg = Column(Text, comment='实际命令中的 creator_id 参数')
