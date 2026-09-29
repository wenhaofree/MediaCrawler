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

使用 `uv` 运行爬虫脚本。创作者采集使用 `--type creator`，关键词搜索使用 `--type search`。

```bash
# 临时关闭代理的方式
NO_PROXY=.douyin.com,douyin.com,www.douyin.com uv run main.py --platform dy --lt qrcode --type creator --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"

# 直接使用：
uv run main.py --platform dy --lt qrcode --type creator --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"  --max_pages 3

uv run main.py --platform bili --lt qrcode --type creator --creator_id "625267185" --max_pages 3

uv run main.py --platform xhs --lt qrcode --type creator --creator_id "https://www.xiaohongshu.com/user/profile/640c29eb000000001001c91b?xsec_token=ABhC5chjrgmTjNDSBeeLLNtrpvHHHA3Zz8u3s5duXIRO0%3D&xsec_source=pc_search"

uv run main.py --platform wb --lt qrcode --type creator --creator_id "5648162302"

uv run main.py --platform zhihu --lt qrcode --type creator --creator_id "morgancheng"

# 闲鱼：当前 MVP 只支持关键词搜索商品，不支持 creator/detail/comment/media
uv run main.py --platform goofish --lt qrcode --type search --keywords "耳机,键盘" --crawler_max_notes_count 30 --save_data_option jsonl

# 七麦：支持关键词搜索、指定 App ID 详情/评论、榜单
uv run main.py --platform qimai --lt qrcode --type search --keywords "微信,小红书" --crawler_max_notes_count 20 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type detail --specified_id "977946724" --get_comment true --max_comments_count_singlenotes 20 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type rank --qimai_rank_type free --qimai_rank_date "2026-09-29" --qimai_rank_genre 6017 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type rank --qimai_rank_type paid --qimai_rank_date "2026-09-29" --qimai_rank_genre 6017 --save_data_option sqlite

```

**参数说明：**

- `--platform`: 指定平台，常用值：`dy` 抖音、`bili` B站、`xhs` 小红书、`wb` 微博、`zhihu` 知乎、`goofish` 闲鱼、`qimai` 七麦。
- `--lt qrcode`: 登录方式为二维码；闲鱼/七麦通常复用 CDP 浏览器会话，遇到登录/风控时在 Chrome 窗口里手动处理。
- `--type creator`: 爬取创作者主页数据。
- `--type search`: 按关键词搜索；闲鱼当前只支持该模式，七麦用于搜索 App。
- `--type detail`: 按指定内容 ID 采集详情；七麦传 App ID。
- `--type rank`: 七麦榜单采集。
- `--creator_id`: 目标创作者 ID，支持多个 ID 用英文逗号分隔。
- `--specified_id`: 详情页 ID，七麦填写 App ID，多个 ID 用英文逗号分隔。
- `--keywords`: 搜索关键词，多个关键词用英文逗号分隔。
- `--crawler_max_notes_count`: 最大采集条数；闲鱼每页约 30 条，七麦建议先从 20 或 50 开始。
- `--get_comment true`: 七麦详情模式下同步采集评论。
- `--max_comments_count_singlenotes`: 七麦单个 App 最大评论条数。
- `--qimai_rank_type`: 七麦榜单类型，常用 `free`、`paid`、`grossing`。
- `--qimai_rank_date`: 七麦榜单日期，格式如 `2026-09-29`；留空取页面默认最新。
- `--qimai_rank_genre`: 七麦榜单分类 ID，例如教育分类 `6017`。
- `--qimai_rank_max_count`: 七麦榜单最大采集条数，默认 `0` 表示全量；程序会下滑分页直到没有新数据。
- `--qimai_crawl_interval_sec`: 七麦逐个 App 详情/评论采集的最小间隔，默认 `5` 秒；实际会额外加少量随机等待，降低风控风险。
- `--save_data_option`: 保存方式，常用 `sqlite`、`jsonl`、`csv`、`excel`。

### 闲鱼采集说明

闲鱼使用 `goofish` 平台名，第一版只做商品搜索：

```bash
# SQLite 入库，后续可在 sqlite-viewer 里查看 goofish_item 表
uv run main.py --platform goofish --lt qrcode --type search --keywords "耳机" --crawler_max_notes_count 30 --save_data_option sqlite

# JSONL 文件保存，适合快速验证
uv run main.py --platform goofish --lt qrcode --type search --keywords "耳机,键盘" --crawler_max_notes_count 60 --save_data_option jsonl
```

注意：

- 当前不支持 `--type creator`、`--type detail`、评论采集、二级评论和媒体下载。
- 建议开启 Chrome CDP 后运行，沿用第 1 步的 `--remote-debugging-port=9222`。
- 首次运行如果页面要求登录或安全验证，直接在弹出的 Chrome 窗口里完成，再重新执行命令。
- SQLite 表名：`goofish_item`；JSONL 默认路径：`data/goofish/jsonl/search_contents_日期.jsonl`。

### 七麦采集说明

七麦使用 `qimai` 平台名，支持 App 搜索、基础详情、评论和榜单。实现方式是打开真实七麦页面，让网页自己发起接口请求，程序优先截获 `api.qimai.cn` 返回的 JSON；详情和评论会额外读取页面 DOM 中已经渲染的数据，不维护 `analysis` 签名逆向逻辑。

```bash
# 搜索 App 并入库
uv run main.py --platform qimai --lt qrcode --type search --keywords "微信,小红书" --crawler_max_notes_count 20 --save_data_option sqlite

# 采集指定 App ID 的基础详情
uv run main.py --platform qimai --lt qrcode --type detail --specified_id "414478124,333206289" --save_data_option sqlite

# 采集详情并同步采集评论，评论会写入 qimai_comment 表
uv run main.py --platform qimai --lt qrcode --type detail --specified_id "977946724" --get_comment true --max_comments_count_singlenotes 40 --save_data_option sqlite

# 采集榜单：类型 + 日期 + 子分类
uv run main.py --platform qimai --lt qrcode --type rank --qimai_rank_type free --qimai_rank_date "2026-09-29" --qimai_rank_genre 6017 --save_data_option sqlite

# 快速验证 JSONL
uv run main.py --platform qimai --lt qrcode --type search --keywords "微信" --crawler_max_notes_count 20 --save_data_option jsonl
```

注意：

- 建议使用第 1 步的 Chrome CDP 模式；七麦依赖真实浏览器页面触发接口。
- 榜单模式会先下滑采完整榜单，再逐个进入 App 详情页采详情和评论。
- 详情/评论采集优先使用七麦前端 SPA 路由切换触发接口，避免每个 App 都整页刷新；失败时才回退到普通页面跳转。
- 当前不支持 `--type creator`、历史趋势、媒体下载。
- 七麦账号权限决定能看到多少数据；如遇登录、滑块或频控，在 Chrome 窗口里人工处理后降低采集量重试。
- SQLite 表名：App/榜单写入 `qimai_app`，评论写入 `qimai_comment`；JSONL 默认路径：`data/qimai/jsonl/*_contents_日期.jsonl` 和 `*_comments_日期.jsonl`。

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
uv run main.py --platform bili --lt qrcode --type creator --max_pages 3 --creator_id "625267185,13416784,39930228,82363089,3493277319825652,12890453,316183842,322961825,385670211,39613022,19484221,3493280364890116,4401694,486989780,520819684,14097567,452959322"

# 微博 (批量采集 5 个账号)
uv run main.py --platform wb --lt qrcode --type creator --max_pages 3 --creator_id "5648162302,1400854834,1660737882,1627825392,1727858283,6182606334"

# 知乎
uv run main.py --platform zhihu --lt qrcode --type creator --max_pages 3 --creator_id "morgancheng"

# 小红书
uv run main.py --platform xhs --lt qrcode --type creator --max_pages 3 --creator_id "640c29eb000000001001c91b,5b4e046811be1031e22f19d8"

# 闲鱼：关键词搜索商品
uv run main.py --platform goofish --lt qrcode --type search --keywords "耳机,键盘" --crawler_max_notes_count 60 --save_data_option sqlite

# 七麦：关键词搜索、详情/评论、榜单
uv run main.py --platform qimai --lt qrcode --type search --keywords "微信,小红书" --crawler_max_notes_count 20 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type detail --specified_id "977946724" --get_comment true --max_comments_count_singlenotes 20 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type rank --qimai_rank_type free --qimai_rank_date "2026-09-29" --qimai_rank_genre 6017 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type rank --qimai_rank_type paid --qimai_rank_date "2026-09-29" --qimai_rank_genre 6017 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type rank --qimai_rank_type grossing --qimai_rank_date "2026-09-29" --qimai_rank_genre 6017 --save_data_option sqlite
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
   - 花生：14097567
   - 木子不写代码：13416784
   - 张咋啦：452959322
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

# 常用命令：

<!-- 环境 -->

source .venv/bin/activate

<!-- 启动 -->

open -na "Google Chrome" --args \
 --remote-debugging-port=9222 \
 --user-data-dir="$HOME/.chrome-cdp-investing"

<!-- 哔哩 -->

uv run main.py --platform bili --lt qrcode --type creator --max_pages 3 --creator_id "625267185,13416784,39930228,82363089,3493277319825652,12890453,316183842,322961825,385670211,39613022,19484221,3493280364890116,4401694,486989780,520819684,14097567"

<!-- 微博 -->

uv run main.py --platform wb --lt qrcode --type creator --max_pages 3 --creator_id "5648162302,1400854834,1660737882,1627825392,1727858283,6182606334"

<!-- 闲鱼 -->

uv run main.py --platform goofish --lt qrcode --type search --keywords "耳机,键盘" --crawler_max_notes_count 60 --save_data_option sqlite

<!-- 七麦 -->

uv run main.py --platform qimai --lt qrcode --type search --keywords "微信,小红书" --crawler_max_notes_count 20 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type detail --specified_id "414478124" --get_comment true --max_comments_count_singlenotes 20 --save_data_option sqlite

uv run main.py --platform qimai --lt qrcode --type rank --qimai_rank_type free --qimai_rank_date "2026-09-29" --qimai_rank_genre 6017 --save_data_option sqlite

<!-- 启动服务 -->

uv run uvicorn api.main:app --port 8080 --reload
