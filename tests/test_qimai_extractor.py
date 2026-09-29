# -*- coding: utf-8 -*-

from media_platform.qimai.help import QimaiExtractor


def test_qimai_extractor_finds_nested_apps_once():
    apps = QimaiExtractor.extract_apps(
        {
            "data": {
                "list": [
                    {
                        "appid": 414478124,
                        "appName": "微信",
                        "publisher": "Tencent",
                        "rating": 4.7,
                    },
                    {"appid": 414478124, "appName": "微信"},
                    {"name": "missing id"},
                ]
            }
        }
    )

    assert len(apps) == 1
    assert apps[0].app_id == "414478124"
    assert apps[0].app_name == "微信"
    assert apps[0].publisher == "Tencent"
    assert apps[0].rating_value == "4.7"
