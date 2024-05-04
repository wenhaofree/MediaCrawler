# 基础配置
PLATFORM = "xhs"
KEYWORDS = "女性耳塞"
# LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
LOGIN_TYPE = "cookie"  # qrcode or phone or cookie
#weibo
# COOKIES = "SINAGLOBAL=9011432937803.672.1702368464142; SCF=AmdJA8eVf6WN0I0DpGYvCRJhTxQLYMoMaSoqxI5y_dhdwYOBpUk0ZxX5VIoDkaNgSyKb6LbktYJ3uUly_0TjWSY.; UOR=,,www.google.com; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WF052.szp5Ep4SBfMjNg4y55JpX5KMhUgL.FozpS0MpSo.ceK52dJLoIEXLxKBLB.eLB.eLxKqLBo5LBoBLxKBLB.eLB.eLxKqLBo-L1h2LxK-LBo.LBoBt; ULV=1710755905126:12:4:1:1855060333663.474.1710755905116:1710235926288; XSRF-TOKEN=GkvVbfaKnTceArW-m0T82ohM; ALF=1713512189; SUB=_2A25I_uGtDeRhGeRP7FUQ9ifKyjyIHXVocntlrDV8PUJbkNB-LXXnkW1NUBLdA2wwxM1c35jgHJs4nhcZTNLN69Ka; WBPSESS=SEf0k1J8BIWQ7VhLTlGU-keH-GtpwsoAaRGD3ZuZ-WyxxrOKseRJmzl8RaQDwpL-5gQ44nPJEV87Fvq7YGSPUZrHQ5SaU9oPrD20J5G7MeLwGWWZqFAYV0a6T1oRl7kcm-DXn83zcJTEjUu9hTBq7Q=="
#xhs
COOKIES = "customerClientId=942802352642599; abRequestId=7f2ce22a-3dba-5b93-9fb8-3e5a2996a2dc; a1=18ba90af086frpd4bszh8l1n6aba415f700r6cgzz30000340284; webId=4f0f6445071a7f3dae555d639002e789; gid=yYD0j80i44W8yYD0j80i88SkYKiFUf4DMuxY8uu1yIK0DFq804y2iK888q48JY484DdKjWdJ; x-user-id-fuwu.xiaohongshu.com=6217407a0000000010008621; x-user-id-school.xiaohongshu.com=6217407a0000000010008621; x-user-id-redlive.xiaohongshu.com=6217407a0000000010008621; customer-sso-sid=65d1a129f600000000000005; x-user-id-pgy.xiaohongshu.com=5b4e046811be1031e22f19d8; x-user-id-ark.xiaohongshu.com=5b4e046811be1031e22f19d8; timestamp2=17083451873324e8549e08a44210e9967e82903c42dce6ed4a95cc049b16d6f; timestamp2.sig=iYLcrseTJqgIdPwehRHZ7tixcwV92OWv2xHey4gVTJA; web_session=040069799c758c3a498e8e4ac4374b797746cb; xsecappid=xhs-pc-web; webBuild=4.7.2; websectiga=f47eda31ec99545da40c2f731f0630efd2b0959e1dd10d5fedac3dce0bd1e04d; sec_poison_id=6c49405b-7be6-4b70-87cc-ce05ab244e07; acw_tc=09f970ed593442a17f9ca33159db63802407f1a859a09d2b125f3d5a841e913e; unread={%22ub%22:%2265f2e6440000000012023ca1%22%2C%22ue%22:%2265e14b29000000000400117d%22%2C%22uc%22:22}"
SORT_TYPE = "popularity_descending"  # 具体值参见media_platform.xxx.field下的枚举值，展示只支持小红书
CRAWLER_TYPE = "search" # 爬取类型，search(关键词搜索) | detail(帖子相亲)| creator(创作者主页数据)

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 设置为True不会打开浏览器（无头浏览器），设置False会打开一个浏览器（小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码）
HEADLESS = True

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 数据保存类型选项配置,支持三种类型：csv、db、json
SAVE_DATA_OPTION = "json"  # csv or db or json

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 指定的浏览器启动路径
EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 20

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 4

# 是否开启爬评论模式, 默认不开启爬评论
ENABLE_GET_COMMENTS = False

# 指定小红书需要爬虫的笔记ID列表
XHS_SPECIFIED_ID_LIST = [
    "6422c2750000000027000d88",
    "64ca1b73000000000b028dd2",
    "630d5b85000000001203ab41",
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

# 指定小红书创作者ID列表
XHS_CREATOR_ID_LIST = [
    "63e36c9a000000002703502b",
    # ........................
]
