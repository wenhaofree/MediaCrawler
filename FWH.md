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
```

---

## 3. 执行数据爬取
使用 `uv` 运行爬虫脚本。以下示例演示了如何根据 `creator_id` 爬取抖音平台的数据：

```bash
uv run main.py --platform dy --lt qrcode --type creator --creator_id "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk"
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