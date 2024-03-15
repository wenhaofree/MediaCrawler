# 基础配置
PLATFORM = "xhs"  #(xhs | dy | ks | bili)
# PLATFORM = "dy"  #(xhs | dy | ks | bili)
# PLATFORM = "ks"  #(xhs | dy | ks | bili)
# PLATFORM = "bili"  #(xhs | dy | ks | bili)
# KEYWORDS = "python,golang"
KEYWORDS = "稀奇古怪的小玩意"
# KEYWORDS = "打底衫"
LOGIN_TYPE = "cookie"  # qrcode or phone or cookie
# bili
# COOKIES = "_uuid=D573DEBA-CC106-CE78-106102-51010531B41068F85624infoc; buvid3=508C7C16-8D27-7225-5F4D-5C9824206BC188036infoc; b_nut=1688146188; rpdid=|(k|kmkY~ukY0J'uY))u)|luY; buvid4=B387BCA1-0175-DA1D-09F5-897A9656E22A61455-023062922-g%2FJDFC92Uz%2FayYMKK0iaZA%3D%3D; i-wanna-go-back=-1; FEED_LIVE_VERSION=V8; nostalgia_conf=-1; b_ut=5; buvid_fp_plain=undefined; is-2022-channel=1; CURRENT_BLACKGAP=0; CURRENT_QUALITY=120; enable_web_push=DISABLE; header_theme_version=CLOSE; home_feed_column=5; PVID=1; CURRENT_FNVAL=4048; bp_video_offset_391635122=866786836279722009; bp_video_offset_15561221=873720558477377559; fingerprint=acfcf3523ddb101ad959617963f4f677; DedeUserID=391635122; DedeUserID__ckMd5=f7ef4108bc747e99; buvid_fp=acfcf3523ddb101ad959617963f4f677; SESSDATA=68d8e728%2C1718096355%2C29efe%2Ac1CjD5NGs12kiRjupwSjmi1RuhjuQPD3ytA7DfzsD8ZxNCcbyafVBBNryncwgj469bq2ESVm0xYnFRZjZSZU1HSmJnV1h5d2ZTRGdhWjIzWTIyY0VSZzhzN0JJWDkyYzBvMDd4ZGFkc2FnLVlQRWtkQXFsQVVDbDU4THM0SVlvZEowcU41N2tjeFBBIIEC; bili_jct=75ca7535ec0bf025d0c9276324c3350d; sid=6rneth79; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDI4MDM1NzEsImlhdCI6MTcwMjU0NDMxMSwicGx0IjotMX0.2ASiGgirecwovwr--Tjh7X3Zz4WNqv9AImtCmIGF4qw; bili_ticket_expires=1702803511; innersign=0; b_lsid=DE82310D4_18C6BA7E31B; browser_resolution=1920-375"
# 抖音
# COOKIES = "store-region-src=uid; bd_ticket_guard_client_web_domain=2; _bd_ticket_crypt_doamin=2; __security_server_data_status=1; my_rd=2; passport_csrf_token=4381950e9aaf92aea3773951b0ab8a79; passport_csrf_token_default=4381950e9aaf92aea3773951b0ab8a79; d_ticket=fb940ed599f8e47f53d60cc8f3d2fb43d4a9b; s_v_web_id=verify_lrprlrit_99354c27_e7b5_4da1_7616_a9f5bb104612; passport_assist_user=Cjx0-y5Tnlj_-e3O3pSrIKQrkjIWwEvPtMTzTCoZr8VlyfjYXUDllwQsP5wkRWTpyi7NcegX_gllYOYd00MaSgo8lEVjeEilB0fvi83rrZx2TI3E-X_mxGYIZKJbr811VduNuR_lWgItVm5TDE24_DBRQpG4uGtFosAZBLBfEMCyxw0Yia_WVCABIgEDmGGzbg%3D%3D; n_mh=qogyIz1IMic5UHATYbxdbx6ZI5do3HFw90ZV0HdgRwI; sso_uid_tt=9985e806d35b00a264a5e7cbbbce5cc0; sso_uid_tt_ss=9985e806d35b00a264a5e7cbbbce5cc0; toutiao_sso_user=8e7ddeef9f37b68bccecfd12ea9b32da; toutiao_sso_user_ss=8e7ddeef9f37b68bccecfd12ea9b32da; LOGIN_STATUS=1; _bd_ticket_crypt_cookie=75922307b926c172a5ee5c4220c75db6; sid_ucp_v1=1.0.0-KDg5MWRmMWJjNDI2YTc5YTFmYmFkNWJlOTBmMjhkZDJhNTRiYWJhYjcKGQjjiOrh5gEQ8dW8rQYY7zEgDDgCQPEHSAQaAmxxIiAxYzRlNmJjZmJjOTMwYjk2OTA2ODlkN2IyY2RjOTNjMQ; ssid_ucp_v1=1.0.0-KDg5MWRmMWJjNDI2YTc5YTFmYmFkNWJlOTBmMjhkZDJhNTRiYWJhYjcKGQjjiOrh5gEQ8dW8rQYY7zEgDDgCQPEHSAQaAmxxIiAxYzRlNmJjZmJjOTMwYjk2OTA2ODlkN2IyY2RjOTNjMQ; store-region=cn-bj; sid_ucp_sso_v1=1.0.0-KDE3YWM5MzE2ODIxZmFhNzg3ZjkyZThlNDU3ZTRjOTUxNjMyOTM4MjUKHQjjiOrh5gEQ6ILLrgYY7zEgDDCFhYDKBTgCQPEHGgJobCIgOGU3ZGRlZWY5ZjM3YjY4YmNjZWNmZDEyZWE5YjMyZGE; ssid_ucp_sso_v1=1.0.0-KDE3YWM5MzE2ODIxZmFhNzg3ZjkyZThlNDU3ZTRjOTUxNjMyOTM4MjUKHQjjiOrh5gEQ6ILLrgYY7zEgDDCFhYDKBTgCQPEHGgJobCIgOGU3ZGRlZWY5ZjM3YjY4YmNjZWNmZDEyZWE5YjMyZGE; sid_guard=8e7ddeef9f37b68bccecfd12ea9b32da%7C1708310888%7C5184000%7CFri%2C+19-Apr-2024+02%3A48%3A08+GMT; uid_tt=9985e806d35b00a264a5e7cbbbce5cc0; uid_tt_ss=9985e806d35b00a264a5e7cbbbce5cc0; sid_tt=8e7ddeef9f37b68bccecfd12ea9b32da; sessionid=8e7ddeef9f37b68bccecfd12ea9b32da; sessionid_ss=8e7ddeef9f37b68bccecfd12ea9b32da; publish_badge_show_info=%221%2C0%2C0%2C1709796485300%22; ttwid=1%7CM1eiAWveA18GuSjYCOlL1qu6lWO3X7k-t6yVJzZZaso%7C1709796579%7Ca29974766e5b7af00c48f73343982f9ed4771b924c548355d5dad80009f03dc7; csrf_session_id=1a130eecfdf37b9c5c24bdfe93795193; SEARCH_RESULT_LIST_TYPE=%22single%22; pwa2=%220%7C0%7C3%7C0%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.5%7D; douyin.com; device_web_cpu_core=8; device_web_memory_size=8; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; download_guide=%223%2F20240310%2F1%22; strategyABtestKey=%221710150700.409%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAA4vGn9GYu39QeHE_7I1SnaQ_quiciNNmgyhQMdvnvyO8%2F1710172800000%2F0%2F1710150703705%2F0%22; GlobalGuideTimes=%221710150733%7C0%22; xgplayer_device_id=52540198649; xgplayer_user_id=601896758196; dy_swidth=1920; dy_sheight=1080; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1920%2C%5C%22screen_height%5C%22%3A1080%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A8%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A1%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A250%7D%22; passport_fe_beating_status=true; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAA4vGn9GYu39QeHE_7I1SnaQ_quiciNNmgyhQMdvnvyO8%2F1710172800000%2F0%2F1710162662666%2F0%22; __ac_nonce=065ef02eb0010900b2c68; __ac_signature=_02B4Z6wo00f011FCXwQAAIDAA71.HzO7mRdRYluAALHKp1buM1WZiJikUSiiu7gP7DvZbolVpONaMpzVmz1eeAZsukhFUJ96U7Hgwq7n36UE.JdTLJ..bY2eJWv.PoFq-J2pf9serTP0vDDW96; IsDouyinActive=true; home_can_add_dy_2_desktop=%221%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCSDJ0cDduanZuNnFaa0tyRHlDRVNLc2xJcHpsbHVKd3o0RDhTeHVqV1BrU1cvNzR2c2xFZDFnbUJIajhSWW8xYU9tZXk5WGp1TWpSaGExcDJpTU9FNGM9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoxfQ%3D%3D; msToken=BAFuUhyP5vyOefnkR6sBWol9CcTmBW7FURD4oBpO3EMIz1Sf6QOIoDM84tu_wVnO2ZcrTG1TjgNnfD1Q_ZyEHgTUxqZ0EeuOgWc5Idp5pqjTt4MIHeY=; tt_scid=8t8skQKIXzECu.QYdnjLsvZiRL2hY7Dk.IvVxX0BxYHkww42TTpYNJmOY.G6B6qj8391; odin_tt=b6555dc7cb2ae5729c05c6542c945c8c883b5f09fd2adbe7ea337e8c10d4a60e7bf5420ca1ef2a15ffbb3ac8d22c281c20ab0428b9414f7464b614cdb5c0e096; msToken=uAQezf653AwKmNIj-pD5qG-1f35Ejq6W4c3xrGM1KZ8WOFYFr7todLRDaFh0d9aFJ-ROBJ19tT8WZbfxSHU3sHXpX8n23EZ4nl3Z5JhGyRav8Jqj0YA="
# 快手
# COOKIES = "kpf=PC_WEB; clientid=3; did=web_a22a1763da8f1f9290b5644501abb13c; userId=3862465324; kpn=KUAISHOU_VISION; kuaishou.server.web_st=ChZrdWFpc2hvdS5zZXJ2ZXIud2ViLnN0EqAB11cU900QTUnXnKwSJfFL3LMgYLwdjdpVZe7kZi2gZToENC9nCkkGyqaO9eSLcxgXBrB3Q8w3qfRJF7eIWa_HZXuaTYantf7jDgk-aq2KsrqpOc8k2vsbVFtK96vDiSyx8gBCI3IrOio19z15DP79YMAtVyCunCMHeiN3aRfiq4IG-MVzBL3fn2SWo5muA2QaN7druHJZKQj35klFbXlXfBoSsmhEcimAl3NtJGybSc8y6sdlIiBshxelBvd0ShaCVFIHdKLS9yJdM4kshF7W3UfNjjb03igFMAE; kuaishou.server.web_ph=512ab26e0d3df31d30a08ecf1a8049c44079"
# 小红书
COOKIES = "customerClientId=942802352642599; abRequestId=7f2ce22a-3dba-5b93-9fb8-3e5a2996a2dc; a1=18ba90af086frpd4bszh8l1n6aba415f700r6cgzz30000340284; webId=4f0f6445071a7f3dae555d639002e789; gid=yYD0j80i44W8yYD0j80i88SkYKiFUf4DMuxY8uu1yIK0DFq804y2iK888q48JY484DdKjWdJ; x-user-id-fuwu.xiaohongshu.com=6217407a0000000010008621; x-user-id-school.xiaohongshu.com=6217407a0000000010008621; x-user-id-redlive.xiaohongshu.com=6217407a0000000010008621; customer-sso-sid=65d1a129f600000000000005; x-user-id-pgy.xiaohongshu.com=5b4e046811be1031e22f19d8; x-user-id-ark.xiaohongshu.com=5b4e046811be1031e22f19d8; timestamp2=17083451873324e8549e08a44210e9967e82903c42dce6ed4a95cc049b16d6f; timestamp2.sig=iYLcrseTJqgIdPwehRHZ7tixcwV92OWv2xHey4gVTJA; web_session=040069799c758c3a498e8e4ac4374b797746cb; webBuild=4.6.0; xsecappid=xhs-pc-web; acw_tc=0f15e8b90b4811c25b3bce3d625c53b3d78e5bf96b914ec78b71923cd993a12b; unread={%22ub%22:%2265ea5888000000000600c959%22%2C%22ue%22:%2265f2e2bc000000001302715a%22%2C%22uc%22:29}; websectiga=634d3ad75ffb42a2ade2c5e1705a73c845837578aeb31ba0e442d75c648da36a; sec_poison_id=b470d873-63f8-45d2-a8d2-8769a99a791c"
CRAWLER_TYPE = "search"

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 重试时间
RETRY_INTERVAL = 60 * 30  # 30 minutes

# playwright headless
HEADLESS = True

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 指定的浏览器启动路径
EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 爬取视频/帖子的数量控制
# CRAWLER_MAX_NOTES_COUNT = 20
CRAWLER_MAX_NOTES_COUNT = 200
# CRAWLER_MAX_NOTES_COUNT = 2000

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 10

# 每个视频/帖子抓取评论最大条数 (为0则不限制)
MAX_COMMENTS_PER_POST = 10

# 评论关键词筛选(只会留下包含关键词的评论,为空不限制)
COMMENT_KEYWORDS = [
    "我"
    # ........................
]

# 指定小红书需要爬虫的笔记ID列表
XHS_SPECIFIED_ID_LIST = [
    "6422c2750000000027000d88",
    "64ca1b73000000000b028dd2",
    "630d5b85000000001203ab41",
    # ........................
]

# 指定抖音需要爬取的ID列表-
# fwh-指的video的Id,获取评论数据: https://www.douyin.com/video/7280854932641664319
DY_SPECIFIED_ID_LIST = [
    # "7321263283711872294",
    "7202432992642387233"
    # ........................
]

# 指定快手平台需要爬取的ID列表
KS_SPECIFIED_ID_LIST = []

# 指定B站平台需要爬取的视频ID列表
BILI_SPECIFIED_ID_LIST = [
    "416252543",
    "976148468"
    # ........................
]
