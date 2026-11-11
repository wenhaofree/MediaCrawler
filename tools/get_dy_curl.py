# -*- coding: utf-8 -*-
"""
Generate and optionally run a live cURL command to fetch Douyin user profile.
Reads COOKIES directly from config/base_config.py.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from media_platform.douyin.help import (
    douyin_sign_obj,
    generate_ms_token,
    get_web_id,
    parse_creator_info_from_url,
)
from tools import utils
import config


def generate_curl(creator_url_or_id: str):
    # 1. Parse sec_user_id
    try:
        creator_info = parse_creator_info_from_url(creator_url_or_id)
        sec_user_id = creator_info.sec_user_id
    except Exception as e:
        print(f"Error parsing creator URL/ID: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Extract cookie info
    cookie_str = config.COOKIES
    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
    uifid = cookie_dict.get("UIFID") or cookie_dict.get("UIFID_TEMP", "")

    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    # 3. Assemble parameters
    params = {
        "sec_user_id": sec_user_id,
        "publish_video_strategy_type": "2",
        "personal_center_strategy": "1",
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "pc_client_type": "1",
        "version_code": "190600",
        "version_name": "19.6.0",
        "update_version_code": "170400",
        "cookie_enabled": "true",
        "browser_language": "zh-CN",
        "browser_platform": "MacIntel",
        "browser_name": "Chrome",
        "browser_version": "125.0.0.0",
        "browser_online": "true",
        "engine_name": "Blink",
        "os_name": "Mac OS",
        "os_version": "10.15.7",
        "cpu_core_num": "8",
        "device_memory": "8",
        "platform": "PC",
        "webid": cookie_dict.get("webid") or get_web_id(),
        "msToken": cookie_dict.get("msToken") or generate_ms_token(),
    }

    # 4. Generate dynamic a_bogus
    query_str = urllib.parse.urlencode(params)
    a_bogus = douyin_sign_obj.call("sign_datail", query_str, user_agent)
    params["a_bogus"] = a_bogus

    full_url = "https://www.douyin.com/aweme/v1/web/user/profile/other/?" + urllib.parse.urlencode(params)

    # Build curl command
    headers = [
        f"-H 'User-Agent: {user_agent}'",
        f"-H 'Cookie: {cookie_str}'",
        "-H 'Referer: https://www.douyin.com/'",
        "-H 'x-tt-argus: 1'",
    ]
    if uifid:
        headers.append(f"-H 'uifid: {uifid}'")

    curl_command = f"curl -s '{full_url}' \\\n  " + " \\\n  ".join(headers)

    return full_url, headers, curl_command, sec_user_id


def main():
    parser = argparse.ArgumentParser(description="Generate and execute live cURL for Douyin creator profile")
    parser.add_argument(
        "target",
        nargs="?",
        default="MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE",
        help="Douyin creator profile URL or sec_user_id",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Directly run curl and print formatted JSON response",
    )

    args = parser.parse_args()

    full_url, headers, curl_cmd, sec_user_id = generate_curl(args.target)

    print("=" * 60)
    print(f"🎯 目标账号 sec_user_id: {sec_user_id}")
    print("=" * 60)
    print("\n📋 实时生成的 cURL 命令 (已自动附加动态 a_bogus 签名与 Cookies):\n")
    print(curl_cmd)
    print("\n" + "=" * 60)

    if args.run:
        print("\n🚀 正在执行 cURL 请求...\n")
        # Run curl via subprocess
        flat_cmd = ["curl", "-s", full_url]
        # parse headers into list
        for h in headers:
            # strip -H and surrounding quotes
            content = h.replace("-H '", "").rstrip("'")
            flat_cmd.extend(["-H", content])

        try:
            res = subprocess.run(flat_cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            status_code = data.get("status_code")
            if status_code == 0:
                user = data.get("user", {})
                print("✅ 请求成功！账号信息如下：")
                print(f"  • 昵称: {user.get('nickname')}")
                print(f"  • 抖音号: {user.get('unique_id') or user.get('short_id')}")
                print(f"  • 签名: {user.get('signature')}")
                print(f"  • 粉丝数: {user.get('follower_count')}")
                print(f"  • 获赞数: {user.get('total_favorited')}")
                print(f"  • 作品数: {user.get('aweme_count')}")
            else:
                print(f"⚠️ 返回状态码非 0: {status_code}, 详情:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"❌ 执行 cURL 失败: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
