# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/extractor.py
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

import json
import re
from typing import Dict, List, Optional

import humps


class XiaoHongShuExtractor:
    def __init__(self):
        pass

    def extract_note_detail_from_html(self, note_id: str, html: str) -> Optional[Dict]:
        """Extract note details from HTML

        Args:
            html (str): HTML string

        Returns:
            Dict: Note details dictionary
        """
        if "noteDetailMap" not in html:
            # Either a CAPTCHA appeared or the note doesn't exist
            return None

        state = re.findall(r"window.__INITIAL_STATE__=({.*})</script>", html)[
            0
        ].replace("undefined", '""')
        if state != "{}":
            note_dict = humps.decamelize(json.loads(state))
            return note_dict["note"]["note_detail_map"][note_id]["note"]
        return None

    def extract_creator_info_from_html(self, html: str) -> Optional[Dict]:
        """Extract user information from HTML

        Args:
            html (str): HTML string

        Returns:
            Dict: User information dictionary
        """
        match = re.search(
            r"<script>window.__INITIAL_STATE__=(.+)<\/script>", html, re.M | re.S
        )
        if match is None:
            return None
        info = json.loads(match.group(1).replace(":undefined", ":null"), strict=False)
        if info is None:
            return None
        return info.get("user").get("userPageData")

    def extract_creator_notes_from_html(self, html: str, xsec_source: str = "pc_search") -> List[Dict]:
        """Extract creator note list from the profile page HTML snapshot."""
        match = re.search(
            r"<script>window.__INITIAL_STATE__=(.+)<\/script>", html, re.M | re.S
        )
        if match is None:
            return []

        info = json.loads(match.group(1).replace(":undefined", ":null"), strict=False)
        if info is None:
            return []

        raw_notes = info.get("user", {}).get("notes", [])
        normalized_notes: List[Dict] = []
        for note_group in raw_notes:
            if isinstance(note_group, dict):
                note_group = [note_group]
            if not isinstance(note_group, list):
                continue

            for note_item in note_group:
                note_card = note_item.get("noteCard", {}) if isinstance(note_item, dict) else {}
                note_id = note_card.get("noteId") or note_item.get("id")
                note_token = note_item.get("xsecToken") or note_card.get("xsecToken") or ""
                if not note_id or not note_token:
                    continue
                normalized_notes.append(
                    {
                        "note_id": note_id,
                        "xsec_token": note_token,
                        "xsec_source": xsec_source or "pc_search",
                    }
                )
        return normalized_notes
