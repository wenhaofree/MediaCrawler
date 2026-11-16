# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

import os
from pathlib import Path


def _env_number(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _default_weread_cli() -> str:
    configured = (os.getenv("WEREAD_OMNI_CLI") or "").strip()
    # Common local / Debian layouts (skip missing configured path)
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path("/opt/weread-omni/bin/weread-omni.js"),
            Path.home() / "github" / "weread-omni" / "bin" / "weread-omni.js",
            Path("/Users/wenhao/fuwenhao/temp/demo-weread/weread-omni/bin/weread-omni.js"),
        ]
    )
    for path in candidates:
        if path.exists():
            return str(path)
    return configured or "weread-omni"


# Path to weread-omni CLI launcher (Node bin script after npm run build)
WEREAD_OMNI_CLI = _default_weread_cli()

# Web cookie for article read/like stats (weread.qq.com).
# Prefer WEREAD_WEB_COOKIE (same as weread-omni CLI); GZH_WEB_COOKIE is an optional alias.
GZH_WEB_COOKIE = (
    os.getenv("WEREAD_WEB_COOKIE") or os.getenv("GZH_WEB_COOKIE") or ""
).strip().strip("'").strip('"')
WEREAD_WEB_COOKIE = (os.getenv("WEREAD_WEB_COOKIE") or "").strip().strip("'").strip('"')

# Optional WeRead account alias for multi-account CLI (--account)
GZH_WEREAD_ACCOUNT = (os.getenv("GZH_WEREAD_ACCOUNT") or os.getenv("WEREAD_ACCOUNT") or "").strip()

# Comma-separated MP_WXS_* account IDs
GZH_ACCOUNT_IDS = [
    item.strip()
    for item in os.getenv("GZH_ACCOUNT_IDS", "").split(",")
    if item.strip()
]

GZH_STATS_LIMIT = max(1, min(100, int(_env_number("GZH_STATS_LIMIT", 20))))
GZH_ARTICLES_COUNT = max(1, min(100, int(_env_number("GZH_ARTICLES_COUNT", 20))))
GZH_REQUEST_INTERVAL_SEC = max(0.5, _env_number("GZH_REQUEST_INTERVAL_SEC", 1.5))
GZH_CLI_TIMEOUT_SEC = max(30, int(_env_number("GZH_CLI_TIMEOUT_SEC", 120)))
