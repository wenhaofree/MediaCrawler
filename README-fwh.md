# 🔥 MediaCrawler 自媒体爬虫 - 个人定制版 🕷️

> **基于 [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 项目的个人定制版本**
>
> 本项目在原版基础上增加了 Notion 数据同步功能，支持将爬取的数据直接保存到 Notion 数据库中。

## 🌟 项目特色

- 🚀 **多平台支持**: 支持小红书、抖音、快手、B站、微博、贴吧、知乎等7大主流平台
- 📊 **Notion集成**: 独有的Notion数据同步功能，支持将爬取数据直接保存到Notion数据库
- 🔄 **智能去重**: 基于唯一ID的去重机制，避免重复采集数据
- 💾 **多种存储**: 支持CSV、JSON、MySQL数据库、Notion等多种数据存储方式
- 🎯 **精准爬取**: 支持关键词搜索、指定帖子、创作者主页等多种爬取模式

## 📋 分支说明

| 分支名称 | 用途说明 | 更新时间 | 运行环境 |
|---------|---------|---------|---------|
| **main** | 用于更新最新代码同步 | 持续更新 | 通用 |
| **release** | 终端执行版本，检索和同步Notion数据 | 稳定版 | 命令行 |
| **fwh-dev-v2.0** | IDE程序中执行，检索和同步Notion数据 | 2024年 | IDE开发 |
| **fwh-dev-v3.0** | 2024年09月11日同步原作者代码后保留开发 | 2024-09-11 | IDE开发 |
| **dev-v4-20250310** | 2025年03月10日同步原作者代码后保留开发 | 2025-03-10 | IDE开发 |


## 🚨 使用注意事项

### 平台检测机制
| 平台 | 检测情况 | 解决方案 |
|------|---------|---------|
| 🔴 **小红书** | 速度过快会强制下线 | 控制爬取频率，重新登录 |
| 🟢 **抖音** | 暂时未出现检测 | 正常使用 |
| 🟡 **快手** | 二维码扫码无法登录 | 使用Cookie方式登录 |
| 🟢 **B站** | 运行顺利 | 正常使用 |
| 🟡 **微博** | 偶有限制 | 适当控制频率 |
| 🟢 **贴吧** | 相对稳定 | 正常使用 |
| 🟢 **知乎** | 相对稳定 | 需要Node.js环境 |

### 登录方式说明
- **二维码登录**: 需要手机扫码，部分平台可能需要手动验证
- **Cookie登录**: 推荐方式，稳定性较高
- **手机号登录**: 部分平台支持，需要短信验证

### 重要配置说明
1. **关键词配置**: 在 `config/base_config.py` 中的 `KEYWORDS` 参数
2. **浏览器配置**: 可指定浏览器路径 `executable_path=config.EXECUTABLE_PATH`
3. **数据去重**: 基于 `note_id` 唯一值进行去重处理
4. **Notion集成**: 支持将数据同步到Notion数据库，避免重复采集

## 🎯 功能特性详解

### 支持的平台和功能
| 平台 | 关键词搜索 | 指定帖子 | 二级评论 | 创作者主页 | 登录态缓存 | IP代理池 | 词云图 |
|------|-----------|---------|---------|-----------|-----------|---------|--------|
| 小红书 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 抖音 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 快手 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| B站 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 微博 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 贴吧 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 知乎 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 爬取模式说明
- **🔍 搜索模式 (search)**: 根据关键词搜索相关内容
- **📄 帖子详情 (detail)**: 爬取指定帖子ID的详细信息
- **👤 创作者模式 (creator)**: 爬取指定创作者的主页数据

### 数据存储方式
- **📊 CSV格式**: 保存到 `data/` 目录下的CSV文件
- **🗄️ 数据库**: 支持MySQL数据库存储，具有去重功能
- **📝 JSON格式**: 保存为JSON文件，便于数据处理
- **📋 Notion**: 独有功能，直接同步到Notion数据库

## 📖 小红书爬取示例

### 配置步骤
1. **修改配置文件** (`config/base_config.py`)
   ```python
   PLATFORM = "xhs"                    # 选择平台
   KEYWORDS = "编程副业,编程兼职"        # 搜索关键词
   LOGIN_TYPE = "cookie"               # 登录方式
   CRAWLER_TYPE = "search"             # 爬取类型
   CRAWLER_MAX_NOTES_COUNT = 200       # 爬取数量
   SAVE_DATA_OPTION = "db"             # 存储方式
   ```

2. **程序运行**
   ```bash
   python main.py --platform xhs --lt cookie --type search
   ```

3. **数据输出**
   - ✅ **笔记信息**: 同步到Notion数据库 + 本地存储
   - ✅ **评论信息**: 保存到 `data/xhs/` 目录
   - ✅ **去重记录**: `Notion-xhs.json` 文件记录已同步数据
   - ✅ **数据量**: 默认爬取200条数据



## 🚀 快速开始

### 环境要求
- **Python**: 3.9+ (推荐 3.9.6)
- **Node.js**: 16+ (抖音和知乎爬取必需)
- **操作系统**: Windows/macOS/Linux

### 安装步骤

#### 1. 创建虚拟环境
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

#### 2. 安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装playwright浏览器驱动
playwright install
```

#### 3. 数据库配置 (可选)
如果选择数据库存储，需要配置 `config/db_config.py`:

```python
# MySQL配置
RELATION_DB_HOST = "localhost"
RELATION_DB_PORT = 3306
RELATION_DB_USER = "root"
RELATION_DB_PWD = "your_password"
RELATION_DB_NAME = "media_crawler"
```

然后初始化数据库表结构：
```bash
python db.py
```

#### 4. 基础配置
修改 `config/base_config.py` 文件：

```python
# 基础配置
PLATFORM = "xhs"                           # 平台选择
KEYWORDS = "编程副业,编程兼职"               # 搜索关键词
LOGIN_TYPE = "cookie"                       # 登录方式
CRAWLER_TYPE = "search"                     # 爬取类型
SAVE_DATA_OPTION = "db"                     # 存储方式
CRAWLER_MAX_NOTES_COUNT = 200               # 爬取数量
ENABLE_GET_COMMENTS = True                  # 是否爬取评论
```

#### 5. 运行程序

```bash
# 基础用法 - 关键词搜索
python main.py --platform xhs --lt cookie --type search

# 指定帖子爬取
python main.py --platform xhs --lt cookie --type detail

# 创作者主页爬取
python main.py --platform xhs --lt cookie --type creator

# 查看所有参数
python main.py --help
```

### 命令行参数说明

| 参数 | 选项 | 说明 |
|------|------|------|
| `--platform` | `xhs`, `dy`, `ks`, `bili`, `wb`, `tieba`, `zhihu` | 选择爬取平台 |
| `--lt` | `qrcode`, `phone`, `cookie` | 登录方式 |
| `--type` | `search`, `detail`, `creator` | 爬取类型 |
| `--keywords` | 字符串 | 搜索关键词 |
| `--save_data_option` | `csv`, `db`, `json` | 数据存储方式 |

### 登录方式详解
- **🔍 二维码登录**: 打开对应APP扫码登录，部分平台需要手动验证
- **🍪 Cookie登录**: 从浏览器复制Cookie信息，推荐方式
- **📱 手机号登录**: 输入手机号接收验证码

### 数据输出
程序执行完毕后，数据将保存到以下位置：
- **CSV/JSON**: `data/{platform}/` 目录下
- **数据库**: MySQL数据库中
- **Notion**: Notion数据库中（如果配置）

## 🔧 高级配置

### Notion集成配置
本项目独有的Notion集成功能，需要配置Notion API：

```python
# 在config/base_config.py中添加Notion配置
NOTION_TOKEN = "your_notion_integration_token"
NOTION_DATABASE_ID = "your_database_id"
```

### 代理配置
```python
# IP代理配置
ENABLE_IP_PROXY = True
IP_PROXY_POOL_COUNT = 5
IP_PROXY_PROVIDER_NAME = "kuaidaili"
```

### 性能优化
```python
# 并发控制
MAX_CONCURRENCY_NUM = 3
CRAWLER_MAX_SLEEP_SEC = 2

# 数据量控制
CRAWLER_MAX_NOTES_COUNT = 500
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 20
```

## 🎨 平台特定配置

### 小红书 (XHS)
```python
PLATFORM = "xhs"
KEYWORDS = "编程副业,编程兼职"
XHS_SPECIFIED_NOTE_URL_LIST = [
    "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=xxx&xsec_source=pc_search"
]
XHS_CREATOR_ID_LIST = ["63e36c9a000000002703502b"]
```

### 抖音 (DY)
```python
PLATFORM = "dy"
KEYWORDS = "编程教程,技术分享"
DY_SPECIFIED_ID_LIST = ["7280854932641664319"]
DY_CREATOR_ID_LIST = ["MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE"]
```

### B站 (BILI)
```python
PLATFORM = "bili"
KEYWORDS = "编程,算法"
BILI_SPECIFIED_ID_LIST = ["BV1d54y1g7db"]
BILI_CREATOR_ID_LIST = ["20813884"]
START_DAY = '2024-01-01'
END_DAY = '2024-12-31'
```

## 🛠️ 常见问题解决

### 环境问题
| 问题 | 解决方案 |
|------|---------|
| 缺少Node.js环境 | 安装Node.js 16+版本 |
| playwright安装失败 | 使用 `playwright install --with-deps` |
| 数据库连接失败 | 检查MySQL服务和配置信息 |

### 登录问题
| 平台 | 常见问题 | 解决方案 |
|------|---------|---------|
| 小红书 | 滑块验证失败 | 设置 `HEADLESS = False`，手动验证 |
| 抖音 | 手机号验证 | 准备安卓手机接收验证码 |
| 快手 | 二维码失效 | 使用Cookie登录方式 |

### 数据问题
- **重复数据**: 启用数据库存储，自动去重
- **数据缺失**: 检查网络连接和平台限制
- **Notion同步失败**: 验证API Token和数据库ID

## 📊 项目结构

```
MediaCrawler/
├── 📁 config/              # 配置文件
│   ├── base_config.py      # 基础配置
│   └── db_config.py        # 数据库配置
├── 📁 media_platform/      # 平台实现
│   ├── xhs/               # 小红书
│   ├── douyin/            # 抖音
│   ├── bilibili/          # B站
│   └── ...                # 其他平台
├── 📁 store/              # 数据存储
├── 📁 data/               # 数据输出目录
├── 📄 main.py             # 程序入口
└── 📄 requirements.txt    # 依赖列表
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 免责声明

⚠️ **重要提醒**：
- 本项目仅供学习和研究使用
- 请遵守各平台的使用条款和robots.txt规则
- 不得用于商业用途或大规模爬取
- 使用时请控制请求频率，避免对平台造成负担
- 用户需自行承担使用本项目的法律责任

## 📞 联系方式

- **原项目**: [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)
- **问题反馈**: 请在GitHub Issues中提交
- **功能建议**: 欢迎提交Pull Request

---

⭐ **如果这个项目对你有帮助，请给个Star支持一下！** ⭐
