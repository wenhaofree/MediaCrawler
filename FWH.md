# TODO：
- 添加抖音账号接口✅
- 抖音账号快照✅（`douyin_creator_stats`）
- 抖音视频作品快照✅（`douyin_aweme_stats`）

## 抖音增长快照与分层采集（已落地）

核心表：

- `douyin_creator` / `douyin_creator_stats`（账号涨粉，建议每天 09:00 一次）
- `douyin_aweme` / `douyin_aweme_stats`（视频互动趋势）
- `douyin_aweme_comment`（评论内容，第一版不做评论快照）

采集时段（Asia/Shanghai）：

- `09:00` morning：账号快照 + 新作发现 + 近 7 天视频 detail 快照
- `14:00` afternoon：新作发现 + 近 7 天视频快照
- `22:30` evening：新作发现 + 近 7 天 / 8～30 天 / 30 天以上（周采）

CLI 示例：

```bash
uv run main.py --platform dy --type creator --max_pages 3 --pure_api true \
  --save_data_option postgres --scheduled_slot morning \
  --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"
```

Web 定时任务 `run_time` 可填：`09:00,14:00,22:30`。

- 采集B站数据如何vps多部署docker？ 只是修改配置不同平台；

# 🚀 项目使用指南

按照以下步骤配置并运行数据爬取与展示服务。

## 1. 启动 Chrome 远程调试端口

在终端中执行以下命令，以允许程序通过 CDP (Chrome DevTools Protocol) 控制浏览器：

```bash
open -na "Google Chrome" --args \
    --remote-debugging-port=9222 \
    --user-data-dir="$HOME/.chrome-cdp-investing"

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.chrome-automation"

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

---

## 6. 纯 API + Node 签名微服务模式 (企业级/服务器部署推荐)

### 🌟 模式背景与设计
- **传统 9222 CDP 模式**：强依赖本地已启动的 Chrome 图形界面浏览器，单实例内存占用大（500MB~1GB），部署到 Linux 服务器时因无 GUI 环境极易被平台识别无头特征并拦截。
- **纯 API 模式 (`--pure_api true`)**：彻底剥离 Playwright 与 Chrome，全链路纯异步 HTTP（`httpx`）请求，单次请求仅几 KB 内存，零浏览器崩溃与内存泄漏风险。
- **常驻 Node.js 签名微服务**：零额外 npm 依赖，在 `services/sign_srv/server.js` 中常驻预加载 `libs/douyin.js`。提供异步 HTTP 签名接口，签名性能提升 3 倍（~14ms/次），并内置**熔断与平滑回退机制**（微服务离线时自动降级到本地 execjs，爬虫进程绝不中断）。

---

### 🚀 推荐方式与使用流程

#### 1. 启动常驻 Node.js 签名微服务 (终端 1)
```bash
# 本地或服务器后台启动（默认监听 127.0.0.1:8999）
node services/sign_srv/server.js

# 生产环境建议使用 PM2 守护常驻：
pm2 start services/sign_srv/server.js --name sign-srv
```

#### 2. 配置登录态 (推荐方式 ⭐⭐⭐⭐⭐)
直接将登录 Cookie 写入配置文件 `config/base_config.py`，避免在终端中传递超长字符串导致特殊字符转义：
```python
# config/base_config.py
COOKIES = "passport_csrf_token=xxx; sessionid=你的sessionid; ttwid=xxx; ..."
```

> **如何获取 Cookie**：在 Chrome 浏览器中登录抖音 `https://www.douyin.com/` -> 按 `F12` 打开开发者工具切换到 **Network (网络)** 标签页 -> 刷新页面点击任一请求 -> 在右侧 **Request Headers** 中找到 `Cookie:` 右键选择 **Copy value** 即可。

#### 3. 运行纯 API 采集命令 (终端 2)
```bash
# 纯 API 采集创作者视频 (无需启动 Chrome，不占用 9222 端口)
uv run main.py --platform dy --type creator --max_pages 3 --pure_api true --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"

# 临时传入 Cookie 的方式 (如果未在 base_config.py 中配置)
uv run main.py --platform dy --type creator --max_pages 3 --pure_api true --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk" --cookies "你的完整Cookie"

# 采集账号一整年历史数据 (设置 --max_pages 0 不限页数向历史倒序全量采集)
uv run main.py --platform dy --type creator --max_pages 0 --pure_api true --save_data_option sqlite --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"
```

---

### 🔍 复审与质量核验方式

#### 1. 签名微服务健康检查
```bash
curl http://127.0.0.1:8999/health
# 返回: {"status":"ok","service":"MediaCrawler-Sign-Service","douyin_loaded":true}
```

#### 2. 自动化单元测试与降级核验
```bash
# 验证签名服务通信、断网平滑降级机制、纯 API 参数构造与 pong 探活
uv run pytest tests/test_sign_service.py

# 抖音核心回归测试集
uv run pytest tests/test_douyin_resilience.py tests/test_douyin_url_parse.py tests/test_douyin_argus_header.py tests/test_douyin_no_user_info.py

# 全量测试套件 (400 passed)
uv run pytest tests/
```

#### 3. 数据落库与重复采集核验
- **更新策略（Upsert）**：SQLite / MySQL / Postgres 模式下重复采集**不会跳过**，而是以最新数据（点赞、评论、分享数等）覆盖更新历史记录，并保留最初入库时间 `add_ts`。
- **媒体文件**：已下载过的封面/视频自动比对跳过，不重复消耗带宽。
- **时间范围筛选核验**：启动可视化服务 `uv run uvicorn api.main:app --port 8080 --reload`，访问 [http://127.0.0.1:8080/sqlite-viewer](http://127.0.0.1:8080/sqlite-viewer) 使用【自定义时间】筛选起止日期（例如 `2026-01-01` 至 `2026-12-31`）核验数据。

---

## 7. 常见问题排查与修复记录：

1. **Bilibili 合并冲突语法错误修复**：已清理 `client.py` 中因合并残留的多余 `try:` 与缩进异常代码，并保留带登录态请求 WBI keys 的特性。
2. **Cookie 解析增强**：修复了 `convert_str_cookie_to_dict` 中遇到带有 `=` 的 Base64/UrlEncode Cookie 值被错误丢弃的问题，现改用 `split("=", 1)` 精准提取。
3. **用户资料接口容错**：在创作者抓取循环中增强了 `get_user_info` 的异常保护，避免单个接口波动影响后续整批作品抓取。

# 常用命令：

<!-- 环境 -->

source .venv/bin/activate

<!-- 启动（二选一，同一时刻只能有一个实例占用 9222 端口） -->

# 选项 1：投资配置环境
# open -na "Google Chrome" --args \
#  --remote-debugging-port=9222 \
#  --user-data-dir="$HOME/.chrome-cdp-investing"

# 选项 2：自动化爬虫环境（常用）
open -na "Google Chrome" --args \
 --remote-debugging-port=9222 \
 --user-data-dir="$HOME/.chrome-automation"

<!-- 抖音 (纯 API + Node 签名微服务模式，不依赖 Chrome 也不占用 9222) -->

# 终端 1 启动签名服务：node services/sign_srv/server.js
# 终端 2 执行采集：
uv run main.py --platform dy --type creator --max_pages 3 --pure_api true --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk,MS4wLjABAAAAqW8dJX9-mXgmeucLFQW9iPwKz8LHOXBnLzscBfG-YBGLIv_lWbdPa3PUfvl9-6Q5,MS4wLjABAAAA7gvThNYc1JhDB1c-2QHBl5NkHE4kNZVMjVp542IZrqtKDikGAJIQMYIfdHujr1iU"

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

<!-- 数据库初始化（如需使用 PostgreSQL） -->

# 确保 .env 中配置了正确的数据库连接信息，然后执行：
uv run main.py --init_db postgres

> 说明：抖音作者表已统一规范命名为 `douyin_creator`（原 `dy_creator` 会在建表/升级时自动无损重命名迁移，代码中保留 `DyCreator = DouyinCreator` 兼容别名）。


