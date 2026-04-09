# 🚀 项目使用指南

按照以下步骤配置并运行数据爬取与展示服务。

## 1. 启动 Chrome 远程调试端口
在终端中执行以下命令，以允许程序通过 CDP (Chrome DevTools Protocol) 控制浏览器：

```bash
open -na "Google Chrome" --args \
    --remote-debugging-port=9222 \
    --user-data-dir="$HOME/.chrome-cdp-investing"
```

---

## 2. 配置数据存储方式
编辑项目中的 `base_config.py` 文件，将数据保存选项设置为 **SQLite**：

```python
# base_config.py

# 可选值: "csv", "db", "json", "jsonl", "sqlite", "excel", "postgres"
SAVE_DATA_OPTION = "sqlite"  

# 关闭评论采集
ENABLE_GET_COMMENTS = False
```

---

## 3. 执行数据爬取
使用 `uv` 运行爬虫脚本。以下示例演示了如何根据 `creator_id` 爬取抖音平台的数据：

```bash
# 临时关闭代理的方式
NO_PROXY=.douyin.com,douyin.com,www.douyin.com uv run main.py --platform dy --lt qrcode --type creator --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"

# 直接使用：
uv run main.py --platform dy --lt qrcode --type creator --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"  --max_pages 3 

uv run main.py --platform bili --lt qrcode --type creator --creator_id "625267185" --max_pages 3 

uv run main.py --platform xhs --lt qrcode --type creator --creator_id "https://www.xiaohongshu.com/user/profile/640c29eb000000001001c91b?xsec_token=ABhC5chjrgmTjNDSBeeLLNtrpvHHHA3Zz8u3s5duXIRO0%3D&xsec_source=pc_search"

uv run main.py --platform wb --lt qrcode --type creator --creator_id "5648162302"

uv run main.py --platform zhihu --lt qrcode --type creator --creator_id "morgancheng"

```

**参数说明：**
* `--platform dy`: 指定平台为抖音。
* `--lt qrcode`: 登录方式为二维码。
* `--type creator`: 爬取类型为创作者。
* `--creator_id`: 目标创作者的具体 ID。

---

## 4. 启动可视化验证服务
数据爬取完成后，可以启动 Uvicorn 服务来查看本地存储的数据：

### 启动服务
```bash
uv run uvicorn api.main:app --port 8080 --reload
```

### 查看数据
服务启动后，请在浏览器中访问以下地址进入 **SQLite 数据查看器**：

👉 [http://127.0.0.1:8080/sqlite-viewer](http://127.0.0.1:8080/sqlite-viewer)

### 定时任务配置：
- 前提是打开9222浏览器端口，并登录对应平台账号
http://127.0.0.1:8080/schedule-tasks




### 一次性批量采集命令 (支持多 ID)：
```bash
# 抖音 (批量采集 3 个账号)
uv run main.py --platform dy --lt qrcode --type creator --max_pages 3 --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk,MS4wLjABAAAAqW8dJX9-mXgmeucLFQW9iPwKz8LHOXBnLzscBfG-YBGLIv_lWbdPa3PUfvl9-6Q5,MS4wLjABAAAA7gvThNYc1JhDB1c-2QHBl5NkHE4kNZVMjVp542IZrqtKDikGAJIQMYIfdHujr1iU"

# B站 (批量采集 14 个账号)
uv run main.py --platform bili --lt qrcode --type creator --max_pages 3 --creator_id "625267185,39930228,82363089,3493277319825652,12890453,316183842,322961825,385670211,39613022,19484221,3493280364890116,4401694,486989780,520819684"

# 微博 (批量采集 5 个账号)
uv run main.py --platform wb --lt qrcode --type creator --max_pages 3 --creator_id "5648162302,1400854834,1660737882,1627825392,1727858283"

# 知乎
uv run main.py --platform zhihu --lt qrcode --type creator --max_pages 3 --creator_id "morgancheng"

# 小红书
uv run main.py --platform xhs --lt qrcode --type creator --max_pages 3 --creator_id "640c29eb000000001001c91b,5b4e046811be1031e22f19d8"
```


## 5. 采集列表统计：
1. 抖音：
    - 赛文乔伊：MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk
    - 朋克周：MS4wLjABAAAAqW8dJX9-mXgmeucLFQW9iPwKz8LHOXBnLzscBfG-YBGLIv_lWbdPa3PUfvl9-6Q5
    - 赛博小凡：MS4wLjABAAAA7gvThNYc1JhDB1c-2QHBl5NkHE4kNZVMjVp542IZrqtKDikGAJIQMYIfdHujr1iU
2. B站：
    - 零度博客：625267185
    - 熠辉IndieDev:39930228
    - 小宇Boi：82363089
    - AI超元域：3493277319825652
    - 程序员鱼皮：12890453
    - 技术爬爬虾：316183842
    - 黄益贺：322961825
    - 秋芝2046：385670211
    - 赛文乔伊：39613022
    - 朋克周：19484221
    - AI教练振轩:3493280364890116
    - 林亦LYi: 4401694
    - 程序员鱼皮:12890453
    - 老麦的工具库: 486989780
    - 小Lin说: 520819684
3. 小红书：
    - AI教练振轩:9639762311
4. 知乎：
    - 程墨Morgan:https://www.zhihu.com/people/morgancheng
5. 微博：
    - 黄建同学:5648162302
    - ruanyf:1400854834
    - 小北带你飞:1660737882
    - 互联网的那点事：1627825392
    - 宝玉xp：1727858283

### 对标账号：张咋啦
- https://www.youtube.com/@ZaraZhangg
- https://x.com/zarazhangrui
- https://zarazhang.com/
- https://github.com/zarazhangrui
- https://www.xiaohongshu.com/user/profile/59757acd50c4b45e6e9a90df?xsec_token=ABLm9ubP8h5K7BPivaQomdi0CzsZNBtVh3jGWqZicxKH0%3D&xsec_source=pc_search
- 视频号
- 

### 个人账户ID：文浩
- 小红书： 5b4e046811be1031e22f19d8
- B站：391635122
- 微博：2177169610
- 知乎：
- 抖音：MS4wLjABAAAAA9_xiL1Q_Yl0VyuR_y7nWN1h5avCDvSZIpoT1HZ9retKOnkqmTYmAqTXdz-Iuf8a
- 快手：3xeks654q36yck6



## Bug:
1. 微博限制查询条数
2. 抖音查询过程中失败；
3. 小红书采集数据中途失败；
4. 知乎限制条数；
5. B站+知乎OK
6. 定时任务的采集抖音作品没有成功，作者信息采集入库了
