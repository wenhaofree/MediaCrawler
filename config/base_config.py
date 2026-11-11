# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/base_config.py
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

# Basic configuration
PLATFORM = "xhs"  # Platform, xhs | dy | ks | goofish | bili | wb | tieba | zhihu | qimai

# 是否使用海外版小红书 (rednote.com)
# 开启后 API 走 webapi.rednote.com，cookie 域使用 .rednote.com
XHS_INTERNATIONAL = False

KEYWORDS = "编程副业,编程兼职"  # Keyword search configuration, separated by English commas
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = "enter_pc_once=1; web_sign_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ2IjoxLCJpZCI6Ijc3MDY3ODcyOTg4OTc5MjE1NzQiLCJkIjowLCJzIjoiIiwidHMiOjE3OTQzNzYyNTh9.hRQrWSUwIeagRBrKxQzpqIJnmz-COXdgg6jeYlTHWJ0; UIFID_TEMP=963b855e412d3196d1c3a882f7f19fd82d0f634397c778689a74b98535e827301f899d31ebec61079fb24c925146c23f9fe2fd2b20e298c865fc1b692626d08820418688c931fcf2c59c6f3bbf205b3a; s_v_web_id=verify_mwbpamhn_JKbevZ9k_Uoh2_4TdB_8UT5_2RMqDHrD1WK3; hevc_supported=true; bd_ticket_guard_core_version=My4zLjM0LWJldGEuMTA%3D; dy_swidth=1280; dy_sheight=720; fpk1=U2FsdGVkX19qcjcFS9ASiv7t4RDoO9Qcdr6bLQ0/uiJRqRxH20Q0H+8wdAT1x6GdFZh0s0Q5jwfpiygMXwSkuA==; fpk2=7e0a971fa172d680b03b9165ec093c2b; strategyABtestKey=%221794376261.267%22; passport_csrf_token=2f081ea649246f81725133d1da6ac599; passport_csrf_token_default=2f081ea649246f81725133d1da6ac599; ttwid=1%7CX4ELg2dbPA2HzOZKALnbiEnudnZJqQgoTr05gPuDh50%7C1794376262%7C9bd0078f7026da61de604dabc9fbbeec49f295cf64ed15d44f0b44e6db1053c8; bd_ticket_guard_regenerate_keys_time=2026-11-11/13:51:03; bd_ticket_guide_tool=0; passport_assist_user=CjyMkEEr96Hu80kN2MEib1St5tSHX_2Wy17GgFXJfvzCQ1mmtoI2mXIdlTXkxLkdziM7MI4wLyCv26Udai4aSgo8AAAAAAAAAAAAAFEgvZOqTvh4L_xI0ljvpk2KCWbqfVFcTlzl5PKq41GovNcYPJx8FCju_p1zzDhokefYEL-poQ4Yia_WVCABIgEDKAP6cw%3D%3D; n_mh=qogyIz1IMic5UHATYbxdbx6ZI5do3HFw90ZV0HdgRwI; uid_tt=ba9de06b723b6b21d9dfa8a80ad7c876; uid_tt_ss=ba9de06b723b6b21d9dfa8a80ad7c876; sid_tt=04158284026f07654bb83efdd444896a; sessionid=04158284026f07654bb83efdd444896a; sessionid_ss=04158284026f07654bb83efdd444896a; is_staff_user=false; has_biz_token=false; _bd_ticket_crypt_cookie=20261111135322E410A175846AF23484C2; bd_ticket_guard_ticket=hash.nhj3y5MocG6zJtXnxdCXMdWqm5YafIr3iP%2BTeDkCGMw%3D; bd_ticket_guard_pubKey=%7B%22value%22%3A%22BNYkaaqjlkKLtmkpcdEUBL%2BaqBx%2Fgcuag2dKaD%2BClVYtOJUlTv%2BWkvAHTdl%2F%2B5EFMYooGNVoNMxScGBbHkzCpPw%3D%22%2C%22timestamp%22%3A1794376403001%7D; bd_ticket_guard_tssign=%7B%22value%22%3A%22ts.2.70386f8e802914e88205c51696007f52c4cef7aac48e5e844a90a4b74702ea10c4fbe87d2319cf05318624ceda14911ca406dedbebeddb2e30fce8d4fa02575d%22%2C%22timestamp%22%3A1794376403001%7D; login_time=1794376403004; sid_guard=04158284026f07654bb83efdd444896a%7C1794376403%7C5184000%7CSun%2C+10-Jan-2027+05%3A53%3A23+GMT; session_tlb_tag=sttt%7C16%7CBBWChAJvB2VLuD791ESJav_________48socbTh23z8kHyJqvHw_gYwDK8upMWLUbGtAT01r7E4%3D; sid_ucp_v1=1.0.0-KGE5NjdjMDgyZDNkMzllNjE3OWYwOWFmMjY0MDczNTVjODEyN2U5MTQKHwjjiOrh5gEQ04XQ1wYY7zEgDDCFhYDKBTgHQPQHSAQaAmxmIiAwNDE1ODI4NDAyNmYwNzY1NGJiODNlZmRkNDQ0ODk2YQ; ssid_ucp_v1=1.0.0-KGE5NjdjMDgyZDNkMzllNjE3OWYwOWFmMjY0MDczNTVjODEyN2U5MTQKHwjjiOrh5gEQ04XQ1wYY7zEgDDCFhYDKBTgHQPQHSAQaAmxmIiAwNDE1ODI4NDAyNmYwNzY1NGJiODNlZmRkNDQ0ODk2YQ; publish_badge_show_info=%220%2C0%2C0%2C1794376403344%22; DiscoverFeedExposedAd=%7B%7D; UIFID=963b855e412d3196d1c3a882f7f19fd82d0f634397c778689a74b98535e827301f899d31ebec61079fb24c925146c23fcf700c2fb1e1933dc454b256b80b072ec6485c0b446cbe467f21f2a323652483005c85bc2b3d4f3216766cba282ad8c3a220a3183dcd5cce12c537ed5527b396cd90a5e50567d99062fbc09b81a215c13cf0fb862e7b324ecb29f2819d1d5eeda0d6cc06c033baa1c69ed0d1ee3631d3; is_dash_user=1; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.5%7D; bd-ticket-guard-request-tlb-group=none; download_guide=%223%2F20261111%2F0%22; is_dbsc=true; x_tt_token=0004158284026f07654bb83efdd444896a0564f1424d17792c33cd4758b2a945d72ed1de39ca356cc9989b74586bde49369a012e972b5e6a9e85277189bb2bb24837fd12b1f0a001e96e14899e72874d40afaa3e3cba556373d8b254a2233a391e094--0a490a202fadc7ce441ceaced11ae8be95e00e8853c8887d47509f1b802442a7ba23ed0f12203f9cfba8789ac417f4ce826d78d81dc7fc97919c08a3f9883e67e060d301507a18f6b4d309-3.0.4; __ac_nonce=06af418590038c8f33737; __ac_signature=_02B4Z6wo00f01e1XvKgAAIDCg2GRGqWukc3td7gAABGjaa; douyin.com; device_web_cpu_core=10; device_web_memory_size=32; is_support_rtm_web_ts=1; SelfTabRedDotControl=%5B%7B%22id%22%3A%227686788278103574538%22%2C%22u%22%3A36%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227600690334393174079%22%2C%22u%22%3A196%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227674951879230490675%22%2C%22u%22%3A58%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227099613062507792391%22%2C%22u%22%3A755%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227705082834452482075%22%2C%22u%22%3A44%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227502851979274635301%22%2C%22u%22%3A72%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227635295464350304302%22%2C%22u%22%3A116%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227692443095941515300%22%2C%22u%22%3A15%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227678921786263603215%22%2C%22u%22%3A25%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227596403437227477018%22%2C%22u%22%3A51%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227566910980711286810%22%2C%22u%22%3A11%2C%22c%22%3A0%7D%5D; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAA4vGn9GYu39QeHE_7I1SnaQ_quiciNNmgyhQMdvnvyO8%2F1794412800000%2F0%2F1794381915482%2F0%22; biz_trace_id=99f44767; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f2730363137373c343d36313c3234272927676c715a75776a716a666a69273f2763646976602778; bit_env=KBpb6dx5BP9HJyuStB2rYmrFEzR3FBCbJzKPTWkmutQCICp56CE6i9gbVRNK42wQjwkuwbwmPWL-aqlRhzt-Y1xsDWlejN6m2OH3w6Bf_lVmWO1j731NL4j-Ql6CKIMi-1pJeTaQwdKInRpJKZIAoSGmknjJtZR7T-yO79RxHH0gxyuM2CZ4rFxYls637ii4s1kEmT_kvHBj1-xlIiqhI4zyIU3YwN2Lf-eFkrTksCouw3HzY36L0VF8ucglkP0mrycDgRCDfMiNe8nMMCqM6KZXQ_Rua7vfvOl4eT74GwepiNpDdauNSdI9I2rqkVCoXLNhe547IVDDig5fP8F6mkA-HmwvowZp3dikPeotV9b7jSZfKFvoEvFMvsLX6w0hMjHJzMEyPaE1m-OjVkb_M2YvSCcVt-Y8g1zwQGwhCj-pP-WS_C1_8fXCNKw49G2cXZJghiiKL2mK0CzfQSO65deZlbvPoDrTqBPZN6a5_pvCMJGwq8iDm176ELbL9x7xQNC53YvpwJeJ8z006dPsYjzUamBrUVxXczvU6SgAkdI%3D; gulu_source_res=eyJwX2luIjoiNGY3MzM3NWQ0YTBhNTFiMTc5NDYwNDVjYTViNWIyNTRlNTdmNjk1YjNjMzliZDJjM2M0NmJiMDIzN2FhMWI1NiJ9; passport_auth_mix_state=zwpf87i6rzkxg6ax75u5jn78yelp7rbc; __security_mc_1_s_sdk_crypt_sdk=354ab8b0-4b21-bf4f; __security_mc_1_s_sdk_cert_key=327ddc2a-4a93-8847; __security_mc_1_s_sdk_sign_data_key_web_protect=bdf49a85-4bc8-b475; bd-web-sign-page-guard=eyJ0c19zaWduIjoidHMuMi43MDM4NmY4ZTgwMjkxNGU4ODIwNWM1MTY5NjAwN2Y1MmM0Y2VmN2FhYzQ4ZTVlODQ0YTkwYTRiNzQ3MDJlYTEwYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsIndlYl92ZXJzaW9uIjoiMiIsInJlZV9wdWJsaWNfa2V5IjoiQk5Za2FhcWpsa0tMdG1rcGNkRVVCTCthcUJ4L2djdWFnMmRLYUQrQ2xWWXRPSlVsVHYrV2t2QUhUZGwvKzVFRk1Zb29HTlZvTk14U2NHQmJIa3pDcFB3PSIsIndlYl9zaWduX3R5cGUiOiIxIiwicmVxX2NvbnRlbnQiOiJ0aWNrZXQsZG9tYWluLHRpbWVzdGFtcCIsInJlcV9zaWduIjoiNjloM2Z5cjd1TmtxQXJwdmY0K3lkSHQ3dll4S2ZUcFJnZkpuYTBoQ3BKST0iLCJ0aW1lc3RhbXAiOjE3OTQzODE5MjQsInRfdHJ1c3QiOjF9; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1280%2C%5C%22screen_height%5C%22%3A720%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A10%2C%5C%22device_memory%5C%22%3A32%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; IsDouyinActive=true; home_can_add_dy_2_desktop=%220%22; odin_tt=b1cc55352075e80d2544ffd1f51870b7c55684e51e7e021f215e24968b900dbdc6444596e7430f37a91c2ab0549844eb"
CRAWLER_TYPE = (
    "search"  # Crawling type, search (keyword search) | detail (post details) | creator (creator homepage data)
)
# Whether to enable IP proxy
ENABLE_IP_PROXY = False

# Number of proxy IP pools
IP_PROXY_POOL_COUNT = 2

# Proxy IP provider name
IP_PROXY_PROVIDER_NAME = "kuaidaili"  # kuaidaili | wandouhttp | static

# Static proxy configuration (used when IP_PROXY_PROVIDER_NAME is set to "static")
# Format: "http://your_home_domain:port" or "http://user:password@your_home_domain:port"
STATIC_PROXY_URL = ""

# Setting to True will not open the browser (headless browser)
# Setting False will open a browser
# If Xiaohongshu keeps scanning the code to log in but fails, open the browser and manually pass the sliding verification code.
# If Douyin keeps prompting failure, open the browser and see if mobile phone number verification appears after scanning the QR code to log in. If it does, manually go through it and try again.
HEADLESS = False

# Whether to save login status
SAVE_LOGIN_STATE = True

# ==================== 纯 API 模式与签名微服务配置 ====================
# 是否启用纯 API 模式 (无需启动浏览器/无需 Playwright/无需 9222 端口)
ENABLE_PURE_API_MODE = False

# 是否启用 Node.js 签名微服务 (默认开启，若微服务未启动会自动降级为本地 execjs 引擎)
ENABLE_SIGN_SERVICE = True

# Node.js 签名微服务服务地址
SIGN_SERVICE_URL = "http://127.0.0.1:8999"

# ==================== CDP (Chrome DevTools Protocol) 配置 ====================
# 是否启用 CDP 模式 - 使用用户本地的 Chrome/Edge 浏览器进行爬取，具有更好的反检测能力
# 开启后，会自动检测并启动用户的 Chrome/Edge 浏览器，通过 CDP 协议进行控制
# 该方式使用真实浏览器环境，包括用户的扩展、Cookie 和设置，大幅降低被风控检测的风险
ENABLE_CDP_MODE = True

# CDP 调试端口，用于与浏览器通信
# 如果端口被占用，系统会自动尝试下一个可用端口
CDP_DEBUG_PORT = 9222

# Attach-only mode for CDP.
# When enabled, MediaCrawler must attach to an existing browser on CDP_DEBUG_PORT.
# If no reusable browser is available, the task fails instead of launching a new browser.
CDP_ATTACH_ONLY = False

# 自定义浏览器路径（可选）
# 如果为空，系统会自动检测 Chrome/Edge 的安装路径
# Windows 示例: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS 示例: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = ""

# 是否在 CDP 模式下启用无头模式
# 注意：即使设置为 True，某些反检测功能在无头模式下可能无法正常工作
CDP_HEADLESS = False

# 浏览器启动超时时间（秒）
BROWSER_LAUNCH_TIMEOUT = 60

# 是否连接用户已打开的浏览器，而不是启动新的浏览器
# 开启后，程序会连接一个已经启用了远程调试的浏览器
# 用户需要在 Chrome 中开启远程调试：chrome://inspect/#remote-debugging
# 或者使用命令行参数启动 Chrome：--remote-debugging-port=9222
# 这种方式反检测效果最好，因为直接使用用户真实浏览器的所有 Cookie、扩展和浏览历史
CDP_CONNECT_EXISTING = True

# 程序结束时是否自动关闭浏览器
# 设置为 False 可以保持浏览器运行，方便调试
AUTO_CLOSE_BROWSER = True

# Data saving type option configuration, supports: csv, db, json, jsonl, sqlite, excel, postgres. It is best to save to DB, with deduplication function.
SAVE_DATA_OPTION = "postgres"  # csv or db or json or jsonl or sqlite or excel or postgres

# Data saving path, if not specified by default, it will be saved to the data folder.
SAVE_DATA_PATH = ""

# Browser file configuration cached by the user's browser
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# The number of pages to start crawling starts from the first page by default
START_PAGE = 1

# Control the number of crawled videos/posts
CRAWLER_MAX_NOTES_COUNT = 15

# Maximum number of pages to crawl in creator mode.
# 0 means unlimited and keeps the historical behavior.
CRAWLER_MAX_PAGES = 0

# Controlling the number of concurrent crawlers
MAX_CONCURRENCY_NUM = 1

# 是否启用媒体下载（封面、视频，以及图文帖的图片），默认关闭。
# 开启后媒体文件按 {SAVE_DATA_PATH 或 data}/{platform}/media/{内容ID}/ 目录聚合存放。
# 支持的平台：xhs / dy / ks / bili / wb（tieba、zhihu 的数据结构中没有媒体字段，不支持）。
# 命令行开关：--get_media
ENABLE_GET_MEDIA = False

# 是否下载实况照片（Live Photo）随附的视频，统一控制抖音和小红书。
# 仅在 ENABLE_GET_MEDIA 开启时生效；关闭后只下载静态图片，不影响普通视频。
# 视频与静态图配对保存为 001_live.mp4 / 001.jpg，不合成相册实况照片。
DOWNLOAD_LIVE_PHOTO = True

# Whether to enable comment crawling mode. Comment crawling is enabled by default.
ENABLE_GET_COMMENTS = False

# Control the number of crawled first-level comments (single video/post)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# Whether to enable the mode of crawling second-level comments. By default, crawling of second-level comments is not enabled.
# If the old version of the project uses db, you need to refer to schema/tables.sql line 287 to add table fields.
ENABLE_GET_SUB_COMMENTS = False

# word cloud related
# Whether to enable generating comment word clouds
ENABLE_GET_WORDCLOUD = False
# Custom words and their groups
# Add rule: xx:yy where xx is a custom-added phrase, and yy is the group name to which the phrase xx is assigned.
CUSTOM_WORDS = {
    "零几": "年份",  # Recognize "zero points" as a whole
    "高频词": "专业术语",  # Example custom words
}

# Deactivate (disabled) word file path
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# Chinese font file path
FONT_PATH = "./docs/STZHONGS.TTF"

# Crawl interval
CRAWLER_MAX_SLEEP_SEC = 2

# 是否禁用 SSL 证书验证。仅在使用企业代理、Burp Suite、mitmproxy 等会注入自签名证书的中间人代理时设为 True。
# 警告：禁用 SSL 验证将使所有流量暴露于中间人攻击风险，请勿在生产环境中开启。
DISABLE_SSL_VERIFY = False

from .bilibili_config import *
from .xhs_config import *
from .dy_config import *
from .ks_config import *
from .goofish_config import *
from .weibo_config import *
from .tieba_config import *
from .zhihu_config import *
from .qimai_config import *
