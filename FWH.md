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
uv run main.py --platform dy --lt qrcode --type creator --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"

uv run main.py --platform bili --lt qrcode --type creator --creator_id "625267185"

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



## 5. 采集列表统计：
1. 抖音：
    - 赛文乔伊：MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk
    - 朋克周：MS4wLjABAAAAqW8dJX9-mXgmeucLFQW9iPwKz8LHOXBnLzscBfG-YBGLIv_lWbdPa3PUfvl9-6Q5
    - 赛博小凡：MS4wLjABAAAA7gvThNYc1JhDB1c-2QHBl5NkHE4kNZVMjVp542IZrqtKDikGAJIQMYIfdHujr1iU
2. B站：
    - 零度博客：625267185
    - 熠辉IndieDev:39930228
3. 小红书：
    - AI教练振轩:9639762311
4. 知乎：
    - 程墨Morgan:https://www.zhihu.com/people/morgancheng
5. 微博：
    - 黄建同学:5648162302