# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/xhs_config.py
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


import os


def _env_flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_number(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default

# Xiaohongshu platform configuration

# Sorting method, the specific enumeration value is in media_platform/xhs/field.py
SORT_TYPE = "popularity_descending"

# Specify the note URL list, which must carry the xsec_token parameter
XHS_SPECIFIED_NOTE_URL_LIST = [
    "https://www.xiaohongshu.com/explore/6aa3d827000000002802c5c8?xsec_token=YBIq8sY-0_K3BACQ7z57J9xJcdflrd8BAf5_zBeJtFMOQ=&xsec_source=pc_creatormng"
    # ........................
]

# Specify creator IDs or homepage URLs. URLs may carry xsec_token and xsec_source.

XHS_CREATOR_ID_LIST = [
    item.strip() for item in os.getenv("XHS_CREATOR_IDS", "").split(",") if item.strip()
]

# Cookie accounts use conservative defaults: one profile page, one request at a time,
# and irregular pauses. Turn this off only after reviewing the platform's rules.
XHS_SAFE_MODE = _env_flag("XHS_SAFE_MODE", True)
XHS_MAX_PAGES = max(1, int(_env_number("XHS_MAX_PAGES", 1)))
XHS_MAX_CREATORS_PER_RUN = max(1, int(_env_number("XHS_MAX_CREATORS_PER_RUN", 1)))
XHS_REQUEST_INTERVAL_MIN_SEC = max(1.0, _env_number("XHS_REQUEST_INTERVAL_MIN_SEC", 8.0))
XHS_REQUEST_INTERVAL_MAX_SEC = max(
    XHS_REQUEST_INTERVAL_MIN_SEC,
    _env_number("XHS_REQUEST_INTERVAL_MAX_SEC", 15.0),
)
