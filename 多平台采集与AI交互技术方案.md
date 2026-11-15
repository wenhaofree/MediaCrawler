# MediaCrawler 多平台采集部署与受限网络下 AI 数据交互技术方案

本文档针对 **多平台采集隔离部署**、**B站免 Chrome 纯 API 架构演进** 以及 **网络严格受限场景下本地 AI 读取云端数据库** 提供生产级落地技术方案。

> [!IMPORTANT]
> **实施原则**：本方案**不改动 MediaCrawler 任何现有核心源码**，纯粹通过 Docker 编排、配置挂载隔离以及标准通信协议达成目标。

---

## 目录

- [一、多平台采集部署方案（抖音 + B站共存）](#一多平台采集部署方案抖音--b站共存)
  - [1.1 核心配置隔离原理](#11-核心配置隔离原理)
  - [1.2 Docker Compose 双服务部署架构（推荐）](#12-docker-compose-双服务部署架构推荐)
  - [1.3 配置准备与挂载文件编写](#13-配置准备与挂载文件编写)
  - [1.4 启动与验证命令](#14-启动与验证命令)
- [二、B站纯 API 服务器模式（免 Chrome）技术路径](#二b站纯-api-服务器模式免-chrome技术路径)
  - [2.1 抖音与 B 站签名架构对比](#21-抖音与-b-站签名架构对比)
  - [2.2 为什么 B 站纯 API 更加轻量？](#22-为什么-b-站纯-api-更加轻量)
  - [2.3 现有代码架构下的免 Chrome 落地路径](#23-现有代码架构下的免-chrome-落地路径)
- [三、受限网络下本地 AI 获取云端 DB 方案](#三受限网络下本地-ai-获取云端-db-方案)
  - [3.1 网络受限现状与痛点](#31-网络受限现状与痛点)
  - [3.2 方案 A：HTTP / HTTPS RESTful API 模式（最推荐 ⭐⭐⭐⭐⭐）](#32-方案-ahttp--https-restful-api-模式最推荐-)
  - [3.3 方案 B：Cloudflare Tunnel + Hyperdrive 穿透模式（⭐⭐⭐⭐）](#33-方案-bcloudflare-tunnel--hyperdrive-穿透模式)
  - [3.4 两大方案选型决策矩阵](#34-两大方案选型决策矩阵)
- [四、完整实施 SOP 清单](#四完整实施-sop-清单)

---

## 一、多平台采集部署方案（抖音 + B站共存）

### 1.1 核心配置隔离原理

在当前项目中，`config/base_config.py` 和 `config/dy_config.py` 虽然配置了默认的抖音平台参数，但它们属于**回退默认值（Fallback Defaults）**。

MediaCrawler 的实际加载机制优先级如下：
$$\text{启动参数 (CLI / API)} > \text{环境变量 (.env)} > \text{挂载的 base\_config.py} > \text{内置源码默认值}$$

为了让抖音和 B 站两个任务互不干扰，**最优雅、最彻底的方式是在 Docker Compose 中将其拆分为两个独立服务（Service）**：
- **镜像完全复用**：同一个 Docker 镜像，无需重复构建；
- **配置完全隔离**：通过 Docker 只读挂载卷（Volume）为不同容器挂载各自独立的 `base_config.py` 和 `.env`；
- **数据完全汇聚**：两个容器加入相同的 Docker 网络 `wenhao-services`，共享同一个 PostgreSQL 实例 `wenhao-postgres`。

```mermaid
flowchart TD
    subgraph Docker网络: wenhao-services
        DY[容器: mediacrawler-dy :8085] -->|挂载 dy_base_config.py| PG[(PostgreSQL: wenhao-postgres :5432)]
        BILI[容器: mediacrawler-bili :8086] -->|挂载 bili_base_config.py| PG
    end
    
    DY -->|纯 API 定时爬取| DyCloud[抖音开放接口]
    BILI -->|API + Cookie 爬取| BiliCloud[B站数据接口]
```

---

### 1.2 Docker Compose 双服务部署架构（推荐）

在服务器项目根目录的 `docker-compose.yml` 中配置双服务，示例配置如下：

```yaml
version: "3.8"

services:
  # ==========================================
  # 1. 抖音自动化采集服务 (纯 API + 签名微服务)
  # ==========================================
  mediacrawler-dy:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mediacrawler-dy
    restart: unless-stopped
    ports:
      - "${DY_APP_PORT:-8085}:8080" # 映射宿主机 8085 端口
    environment:
      # 数据库连接
      DATABASE_URL: postgresql://${POSTGRES_DB_USER:-postgres}:${POSTGRES_DB_PWD:-fuwenhao}@wenhao-postgres:5432/${POSTGRES_DB_NAME:-media_crawler}
      POSTGRES_DB_HOST: wenhao-postgres
      POSTGRES_DB_PORT: 5432
      POSTGRES_DB_USER: ${POSTGRES_DB_USER:-postgres}
      POSTGRES_DB_PWD: ${POSTGRES_DB_PWD:-fuwenhao}
      POSTGRES_DB_NAME: ${POSTGRES_DB_NAME:-media_crawler}
      SAVE_DATA_OPTION: postgres
      AUTO_INIT_DB: "true"
      TZ: Asia/Shanghai
      SQLITE_DB_PATH: /app/data/sqlite_tables.db

      # 抖音自动化配置
      AUTO_SEED_DY_SCHEDULE: "true"
      SCHEDULED_CRAWL_PURE_API: "true"
      DY_SCHEDULE_RUN_TIME: "09:00,14:00,22:30"
      DY_SCHEDULE_SYNC_FROM_DB: "true"
    volumes:
      - ./data/dy:/app/data
      - ./.env:/app/.env:ro
      - ./config/base_config.py:/app/config/base_config.py:ro
    networks:
      - wenhao-services

  # ==========================================
  # 2. B站自动化采集服务 (独立配置与会话)
  # ==========================================
  mediacrawler-bili:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mediacrawler-bili
    restart: unless-stopped
    ports:
      - "${BILI_APP_PORT:-8086}:8080" # 映射宿主机 8086 端口，独立 Web 控制中心
    environment:
      # 共享相同的数据库实例与库名
      DATABASE_URL: postgresql://${POSTGRES_DB_USER:-postgres}:${POSTGRES_DB_PWD:-fuwenhao}@wenhao-postgres:5432/${POSTGRES_DB_NAME:-media_crawler}
      POSTGRES_DB_HOST: wenhao-postgres
      POSTGRES_DB_PORT: 5432
      POSTGRES_DB_USER: ${POSTGRES_DB_USER:-postgres}
      POSTGRES_DB_PWD: ${POSTGRES_DB_PWD:-fuwenhao}
      POSTGRES_DB_NAME: ${POSTGRES_DB_NAME:-media_crawler}
      SAVE_DATA_OPTION: postgres
      AUTO_INIT_DB: "false" # 由 dy 服务统一初始化即可，避免并行重复建表
      TZ: Asia/Shanghai
      SQLITE_DB_PATH: /app/data/sqlite_tables.db

      # 禁用抖音自动调度，避免重复执行
      AUTO_SEED_DY_SCHEDULE: "false"
    volumes:
      - ./data/bili:/app/data
      - ./.env:/app/.env:ro
      # 核心隔离点：挂载专用的 B 站配置文件
      - ./config/bili_base_config.py:/app/config/base_config.py:ro
    networks:
      - wenhao-services

networks:
  wenhao-services:
    external: true
```

---

### 1.3 配置准备与挂载文件编写

在宿主机的 `config/` 目录下创建 `bili_base_config.py`（直接基于现有的 `base_config.py` 复制）：

```bash
cp config/base_config.py config/bili_base_config.py
```

在 `config/bili_base_config.py` 中，仅需核对/修改如下平台变量：

```python
# config/bili_base_config.py

# 1. 切换平台为 B站
PLATFORM = "bili"

# 2. 爬取类型（creator：创作者主页；search：关键词搜索）
CRAWLER_TYPE = "creator"

# 3. 填入你的 B 站有效 Cookie（在 Chrome 中登录哔哩哔哩后 F12 复制 SESSDATA / bili_jct 等）
COOKIES = "SESSDATA=xxxx; bili_jct=xxxx; buvid3=xxxx; DedeUserID=xxxx; ..."

# 4. 存储方式保持 postgres
SAVE_DATA_OPTION = "postgres"

# 5. 创作者分页与抓取数量控制
CRAWLER_MAX_PAGES = 3
CRAWLER_MAX_NOTES_COUNT = 30
ENABLE_GET_COMMENTS = False
```

---

### 1.4 启动与验证命令

```bash
# 1. 启动两个采集服务（构建镜像后后台运行）
docker compose up -d

# 2. 检查两组容器运行状态
docker compose ps
# 期望看到：
# mediacrawler-dy     Up   0.0.0.0:8085->8080/tcp
# mediacrawler-bili   Up   0.0.0.0:8086->8080/tcp

# 3. 查看各自日志
docker compose logs -f mediacrawler-dy
docker compose logs -f mediacrawler-bili

# 4. 访问各自独立的控制中心：
# 抖音控制中心: http://服务器IP:8085/schedule-tasks
# B站控制中心:  http://服务器IP:8086/schedule-tasks
```

---

## 二、B站纯 API 服务器模式（免 Chrome）技术路径

### 2.1 抖音与 B 站签名架构对比

| 对比维度 | 抖音平台 | B站平台（Bilibili） |
| :--- | :--- | :--- |
| **反爬核心签名** | `a_bogus`、`msToken` | `w_rid`、`wts` (Wbi 签名体系) |
| **签名计算环境** | 强混淆 JS 代码，必须依赖 Node.js 微服务常驻运行 | **纯 Python 原生算法即可完成**（MD5 散列计算） |
| **Wbi 密钥获取** | 无公开获取途径，需动态 hook 网页上下文 | 通过开放接口 `GET /x/web-interface/nav` 直接下发 |
| **纯 API 复杂度** | 较高（需维护 Node 签名微服务与 RPC 通信） | **极低（全链路纯 HTTP 异步请求即可跑通）** |

---

### 2.2 为什么 B 站纯 API 更加轻量？

1. **算法已在代码中就绪**：
   在项目文件的 [media_platform/bilibili/help.py](file:///Users/wenhao/fuwenhao/github/MediaCrawler/media_platform/bilibili/help.py) 中，`BilibiliSign` 类已经完整实现了基于 `img_key` 和 `sub_key` 的 Wbi 参数加签。无需调用外部 Node.js 进程。
2. **密钥获取天然具备 HTTP 回退机制**：
   在 [media_platform/bilibili/client.py](file:///Users/wenhao/fuwenhao/github/MediaCrawler/media_platform/bilibili/client.py#L191-L200) 中，已内置如下逻辑：当无法从浏览器 `localStorage` 提取密钥时，会自动向 `https://api.bilibili.com/x/web-interface/nav` 发起 `httpx` GET 请求取得最新密钥。
3. **数据请求全部为异步 REST API**：
   B 站作品搜索、UP 主视频列表（`/x/space/wbi/arc/search`）、视频基础信息（`/x/web-interface/view`）全部是标准的 JSON 接口，底层使用 `httpx.AsyncClient`。

---

### 2.3 现有代码架构下的免 Chrome 落地路径

当前代码中唯一阻碍“彻底去浏览器”的原因，是 `media_platform/bilibili/core.py` 的入口处包裹了 `async with async_playwright()` 用于弹出二维码登录窗口。

#### 当前无需改动源码的最佳应对策略：
在 `bili_base_config.py` 中直接提供有效的静态登录 Cookie（含 `SESSDATA`）：
1. 容器运行 `BilibiliCrawler` 时，底层通过 Cookie 执行一次轻量探活（`bili_client.pong()`）；
2. 只要 Cookie 有效，系统直接进入后续抓取流程，不会触发弹出扫码或人工滑块；
3. 后续所有几千条视频列表、播放统计、互动量抓取**全部走底层 `httpx` API 传输**，浏览器不会加载任何重度视频流媒体资源，服务器内存占用极小。

---

## 三、受限网络下本地 AI 获取云端 DB 方案

### 3.1 网络受限现状与痛点

在当前场景下：
- ❌ **5432 端口被拦截**：服务器未向公网直接开放 PostgreSQL 原生端口；
- ❌ **禁止 SSH 直连**：安全策略或无公网 IP 限制，无法建立本地到服务器的 `ssh -L` 端口转发隧道；
- ✅ **允许 HTTP/HTTPS 访问**：服务器的 Web 服务（如 8085 / 8086）或反向代理域名是正常可连通的。

```mermaid
flowchart TD
    subgraph 本地客户端
        LocalAI["本地 AI / 智能体 / Cursor / Python 分析"]
    end

    subgraph 网络防火墙屏障
        FW["安全防火墙 (阻断 5432 与 SSH 入站)"]
    end

    subgraph 云端服务器
        subgraph 方案 A: HTTP REST API
            FastAPI["FastAPI 业务数据接口 (:8085)"]
        end

        subgraph 方案 B: Cloudflare Tunnel
            CFTunnel["cloudflared 出站长连接"]
        end

        PG[("PostgreSQL: wenhao-postgres")]
    end

    LocalAI -.->|❌ 被拦截| FW
    LocalAI ===>|✅ 方案 A: 走标准 HTTP/HTTPS 请求| FastAPI
    FastAPI -->|内网高速查询| PG

    CFTunnel ==>|反向加密出站穿透| CloudflareCloud["Cloudflare 边缘网络"]
    CloudflareCloud ===>|✅ 方案 B: 映射到本地 TCP| LocalAI
    CFTunnel --> PG
```

---

### 3.2 方案 A：HTTP / HTTPS RESTful API 模式（最推荐 ⭐⭐⭐⭐⭐）

#### 1. 为什么 REST API 是 AI 的天然搭档？
- **零安全暴露风险**：无需将底层数据库直接暴露至外网，避免全库读写凭据泄露或被 SQL 注入。
- **标准化 Tool Call / Function Calling**：现代 AI 智能体（如 LangChain、LlamaIndex、OpenAI Function Calling、Dify）均以 OpenAPI / REST 协议作为外部工具调用的第一公民。
- **数据结构裁剪与聚合**：API 可以在服务端预先完成快照差值计算（如“近 24 小时涨粉量”），直接向 AI 返回精简 JSON，极大节约 LLM 的 Token 消耗。

#### 2. 本地 AI 代码调用示例
本地 AI 分析脚本或 Agent 只需通过标准的 HTTP 请求获取结构化数据：

```python
import httpx
import pandas as pd

# 1. 本地 AI 请求服务器已开放的 HTTP 接口
API_BASE_URL = "http://你的服务器IP:8085"

def fetch_creator_growth(creator_id: str) -> pd.DataFrame:
    """获取指定博主的增长快照数据"""
    url = f"{API_BASE_URL}/api/douyin/creator/stats"
    response = httpx.get(url, params={"creator_id": creator_id, "limit": 30}, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    # 转换为 DataFrame 供数据分析与可视化
    return pd.DataFrame(data.get("items", []))

# 2. 传递给 LLM 进行智能总结分析
def run_ai_summary(creator_id: str):
    df = fetch_creator_growth(creator_id)
    prompt = f"以下是创作者 {creator_id} 近期的互动与粉丝增长数据，请分析其近期爆款趋势：\n{df.to_markdown()}"
    # 调用大模型生成洞察...
```

---

### 3.3 方案 B：Cloudflare Tunnel + Hyperdrive 穿透模式（⭐⭐⭐⭐）

如果你提到的 **"hypedriver"** 是指 **Cloudflare Hyperdrive** 与 **Cloudflare Tunnel (`cloudflared`)**，这是在入站端口完全封闭场景下，实现**原生数据库连接穿透**的工业级方案。

#### 1. 核心工作原理
- **无需公网 IP，无需入站开放**：服务器安装轻量守护程序 `cloudflared`，主动向 Cloudflare 全球边缘节点发起**出站长连接（Outbound Tunnel）**。
- **安全身份认证**：通过 Cloudflare Zero Trust 鉴权，外部未授权流量完全无法触达服务器。

#### 2. 部署操作流程

1. **服务器端拉起 Tunnel（仅需一条 Docker 命令）**：
   在服务器上将 `cloudflared` 容器加入 `wenhao-services` 网络，打通内网：
   ```bash
   docker run -d --name cloudflared --network wenhao-services \
     cloudflare/cloudflared:latest tunnel --no-autoupdate run --token <你的_CLOUDFLARE_TUNNEL_TOKEN>
   ```
2. **在 Cloudflare 控制台配置私有主机名路由**：
   - 域名：`db.yourdomain.com`
   - 服务协议：`TCP`
   - URL：`wenhao-postgres:5432`
3. **本地客户端端口映射**：
   本地电脑只需安装 `cloudflared`，运行：
   ```bash
   cloudflared access tcp --hostname db.yourdomain.com --url localhost:15432
   ```
4. **本地 AI 直接通过标准驱动连接**：
   本地 AI 脚本可以像操作本地数据库一样，直连本地 `15432` 端口：
   ```python
   from sqlalchemy import create_engine
   
   # 本地映射端口直连，底层经由 Cloudflare 加密出站隧道穿透到云端数据库
   engine = create_engine("postgresql://postgres:fuwenhao@localhost:15432/media_crawler")
   ```

#### 3. Cloudflare Hyperdrive 的辅助作用
如果你的 AI 系统运行在云端 Serverless 环境（如 Cloudflare Workers / Vercel）：
- Cloudflare Hyperdrive 充当智能数据库连接池与查询缓存中间件；
- 它将全球分布式请求汇聚并缓存常见 SQL，极大降低远程数据库连接握手开销（缩短高达 80% 的延迟）。

---

### 3.4 两大方案选型决策矩阵

| 评估维度 | 方案 A：HTTP RESTful API | 方案 B：Cloudflare Tunnel 穿透 |
| :--- | :--- | :--- |
| **网络穿透难度** | 零门槛，复用服务器已有的 HTTP 端口 | 需拥有一个托管在 Cloudflare 的域名 |
| **本地 AI 适配性** | **极高**（天然适配 Function Calling / Tools） | 适配传统 ORM、SQL 分析工具与 DBeaver |
| **权限控制** | **精细**（只读接口、字段裁剪、参数过滤） | 粗粒度（直接暴露整个数据库表结构） |
| **Token 消耗优化** | **优秀**（服务端做聚合计算后只返回最终结果） | 一般（AI 容易直接查出几万行原始数据塞爆上下文） |
| **运维成本** | 仅需增加几个查询 API | 需在服务器与本地同时守护 `cloudflared` 进程 |

> [!TIP]
> **结论**：
> - 绝大多数 AI Agent、RAG 检索和数据报表应用，**首选方案 A（REST API）**；
> - 如果本地必须使用 DBeaver、Navicat 或复杂的 Text-to-SQL 全库模式，**采用方案 B（Cloudflare Tunnel）**。

---

## 四、完整实施 SOP 清单

1. **多采集部署实施**：
   - [ ] 复制 `config/bili_base_config.py`，配置 B 站 `PLATFORM = "bili"` 与有效 `COOKIES`；
   - [ ] 更新 `docker-compose.yml`，定义 `mediacrawler-dy` (8085) 与 `mediacrawler-bili` (8086) 两个服务；
   - [ ] 执行 `docker compose up -d` 启动，确认两组服务各自正常运行。
2. **受限网络数据读取实施**：
   - [ ] 优先通过服务器 WebUI/API 端口（如 8085）调取数据；
   - [ ] 若需本地直连，注册 Cloudflare 免费版并启动 `cloudflared` 容器建立 TCP 私有隧道。
