# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler

import time
from typing import Optional

import httpx

import config
from tools import utils


class SignServiceClient:
    """Client for calling external Node.js signature microservice."""

    _last_failure_time: float = 0.0
    _failure_cooldown_seconds: float = 10.0  # Avoid repeated timeouts when service is offline

    @classmethod
    def is_available(cls) -> bool:
        if not getattr(config, "ENABLE_SIGN_SERVICE", True):
            return False
        # If recently failed, temporarily avoid calling to avoid slowing down crawling
        if time.time() - cls._last_failure_time < cls._failure_cooldown_seconds:
            return False
        return True

    @classmethod
    async def get_douyin_a_bogus(
        cls,
        url: str,
        params: str,
        user_agent: str,
    ) -> Optional[str]:
        """
        Request Douyin a_bogus from Node.js signature microservice.
        Returns a_bogus string if successful, or None if service is unavailable/fails.
        """
        if not cls.is_available():
            return None

        sign_srv_url = getattr(config, "SIGN_SERVICE_URL", "http://127.0.0.1:8999").rstrip("/")
        endpoint = f"{sign_srv_url}/sign"

        payload = {
            "url": url,
            "params": params,
            "user_agent": user_agent,
        }

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 0 and data.get("a_bogus"):
                        return data["a_bogus"]
                    utils.logger.warning(
                        f"[SignServiceClient] Sign service returned non-zero code or empty a_bogus: {data}"
                    )
                else:
                    utils.logger.warning(
                        f"[SignServiceClient] Sign service returned status {resp.status_code}: {resp.text}"
                    )
        except Exception as exc:
            cls._last_failure_time = time.time()
            utils.logger.warning(
                f"[SignServiceClient] Failed to connect to sign microservice at {endpoint}: {exc}. "
                f"Falling back to local execjs signature engine (cooldown {cls._failure_cooldown_seconds}s)."
            )

        return None

