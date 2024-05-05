# 基础配置
PLATFORM = "xhs"
KEYWORDS = "AI"
LOGIN_TYPE = "cookie"  # qrcode or phone or cookie
COOKIES = "unread={%22ub%22:%22663378e0000000001e0301f9%22%2C%22ue%22:%22661cda0e000000001a016da8%22%2C%22uc%22:22}; web_session=040069b4a6fd1d43a7061fb303344b03cb103e; gid=yYi4KSK80JC0yYi4KSK8yxv022j2jFCCkIfCx4UACl04xiq873lI9U888J24WWK8Kj4i4K2D; sec_poison_id=0452d232-f2da-4c1c-81f1-fc95a3f7b295; websectiga=8886be45f388a1ee7bf611a69f3e174cae48f1ea02c0f8ec3256031b8be9c7ee; acw_tc=6e877f5428a07d155c18fe3b656bc6627f4f013076b8341f8e3a9592cf520074; a1=18f46c60155959rxxgndxqxoa4huiontxhhfpya4p30000254776; webBuild=4.14.2; webId=598f9d48f8175990c432da097a5e8c46; xsecappid=xhs-pc-web; abRequestId=8ee366a5-328b-5c9a-bcda-05fe5c638a46"
SORT_TYPE = "popularity_descending"  # 具体值参见media_platform.xxx.field下的枚举值，展示只支持小红书  基础: general  流行: popularity_descending  最新: time_descending
CRAWLER_TYPE = "creator"  # 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)

# 自定义添加浏览器内核
EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"

# 设置为True不会打开浏览器（无头浏览器），设置False会打开一个浏览器（小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码）
HEADLESS = True

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 数据保存类型选项配置,支持三种类型：csv、db、json
SAVE_DATA_OPTION = "json"  # csv or db or json

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 20

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 4

# 是否开启爬图片模式, 默认不开启爬图片
ENABLE_GET_IMAGES = False

# 是否开启爬评论模式, 默认不开启爬评论
ENABLE_GET_COMMENTS = False

# 是否开启爬二级评论模式, 默认不开启爬二级评论, 目前仅支持 xhs
# 老版本项目使用了 db, 则需参考 schema/tables.sql line 287 增加表字段
ENABLE_GET_SUB_COMMENTS = False

# 指定小红书需要爬虫的笔记ID列表(对应:detail)
XHS_SPECIFIED_ID_LIST = [
    "6422c2750000000027000d88",
    # "64ca1b73000000000b028dd2",
    # "630d5b85000000001203ab41",
    # ........................
]

# 指定抖音需要爬取的ID列表
DY_SPECIFIED_ID_LIST = [
    "7280854932641664319",
    "7202432992642387233"
    # ........................
]

# 指定快手平台需要爬取的ID列表
KS_SPECIFIED_ID_LIST = [
    "3xf8enb8dbj6uig",
    "3x6zz972bchmvqe"
]

# 指定B站平台需要爬取的视频bvid列表
BILI_SPECIFIED_ID_LIST = [
    "BV1d54y1g7db",
    "BV1Sz4y1U77N",
    "BV14Q4y1n7jz",
    # ........................
]

# 指定微博平台需要爬取的帖子列表
WEIBO_SPECIFIED_ID_LIST = [
    "4982041758140155",
    # ........................
]

# 指定小红书创作者ID列表(对应:creator)
XHS_CREATOR_ID_LIST = [
    "57b0179250c4b4478b6e02dd",
    "5b3717f011be104bc9f72c5f",
    "5fe621500000000001002a93",
    # ........................
]
