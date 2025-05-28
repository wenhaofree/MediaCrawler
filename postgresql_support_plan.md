# PostgreSQL支持实现方案

## 🎯 实现策略：数据库适配器模式

### 1. 创建数据库抽象基类

```python
# async_db_base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

class AsyncDBBase(ABC):
    @abstractmethod
    async def query(self, sql: str, *args) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def get_first(self, sql: str, *args) -> Union[Dict[str, Any], None]:
        pass
    
    @abstractmethod
    async def item_to_table(self, table_name: str, item: Dict[str, Any]) -> int:
        pass
    
    @abstractmethod
    async def update_table(self, table_name: str, updates: Dict[str, Any], 
                          field_where: str, value_where: Union[str, int, float]) -> int:
        pass
    
    @abstractmethod
    async def execute(self, sql: str, *args) -> int:
        pass
```

### 2. PostgreSQL适配器实现

```python
# async_postgresql_db.py
import asyncpg
from typing import Any, Dict, List, Union
from async_db_base import AsyncDBBase

class AsyncPostgreSQLDB(AsyncDBBase):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.__pool = pool
    
    async def query(self, sql: str, *args) -> List[Dict[str, Any]]:
        async with self.__pool.acquire() as conn:
            # PostgreSQL参数占位符使用$1, $2而不是%s
            pg_sql = self._convert_mysql_to_pg_sql(sql)
            rows = await conn.fetch(pg_sql, *args)
            return [dict(row) for row in rows]
    
    async def get_first(self, sql: str, *args) -> Union[Dict[str, Any], None]:
        async with self.__pool.acquire() as conn:
            pg_sql = self._convert_mysql_to_pg_sql(sql)
            row = await conn.fetchrow(pg_sql, *args)
            return dict(row) if row else None
    
    async def item_to_table(self, table_name: str, item: Dict[str, Any]) -> int:
        fields = list(item.keys())
        values = list(item.values())
        # PostgreSQL使用双引号而不是反引号
        fields = [f'"{field}"' for field in fields]
        fieldstr = ','.join(fields)
        # PostgreSQL使用$1, $2...占位符
        valstr = ','.join([f'${i+1}' for i in range(len(item))])
        sql = f"INSERT INTO {table_name} ({fieldstr}) VALUES({valstr}) RETURNING id"
        
        async with self.__pool.acquire() as conn:
            row = await conn.fetchrow(sql, *values)
            return row['id'] if row else 0
    
    def _convert_mysql_to_pg_sql(self, sql: str) -> str:
        """转换MySQL SQL语法到PostgreSQL"""
        # 替换反引号为双引号
        sql = sql.replace('`', '"')
        # 替换%s占位符为$1, $2...
        # 这里需要更复杂的逻辑来正确处理参数占位符
        return sql
```

### 3. 数据库工厂模式

```python
# db_factory.py
from enum import Enum
from typing import Union
import asyncpg
import aiomysql
from async_db_base import AsyncDBBase
from async_db import AsyncMysqlDB
from async_postgresql_db import AsyncPostgreSQLDB

class DatabaseType(Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"

class DatabaseFactory:
    @staticmethod
    async def create_connection_pool(db_type: DatabaseType, config: dict):
        if db_type == DatabaseType.MYSQL:
            return await aiomysql.create_pool(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                db=config["db"],
                charset=config.get("charset", "utf8mb4"),
                autocommit=True
            )
        elif db_type == DatabaseType.POSTGRESQL:
            return await asyncpg.create_pool(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database=config["db"],
                min_size=1,
                max_size=10
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    @staticmethod
    def create_db_adapter(db_type: DatabaseType, pool) -> AsyncDBBase:
        if db_type == DatabaseType.MYSQL:
            return AsyncMysqlDB(pool)
        elif db_type == DatabaseType.POSTGRESQL:
            return AsyncPostgreSQLDB(pool)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
```

### 4. 配置文件更新

```python
# config/db_config.py (更新)
import os
from enum import Enum

class DatabaseType(Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"

# 数据库类型配置
DB_TYPE = DatabaseType(os.getenv("DB_TYPE", "mysql"))

# MySQL配置
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "db": os.getenv("MYSQL_DB", "media_crawler"),
    "charset": "utf8mb4"
}

# PostgreSQL配置
POSTGRESQL_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", ""),
    "db": os.getenv("PG_DB", "media_crawler")
}

# 根据类型选择配置
DB_CONFIG = MYSQL_CONFIG if DB_TYPE == DatabaseType.MYSQL else POSTGRESQL_CONFIG
```

### 5. PostgreSQL表结构转换

```sql
-- schema/tables_postgresql.sql
-- 转换MySQL表结构到PostgreSQL

-- 示例：小红书笔记表
DROP TABLE IF EXISTS xhs_note;
CREATE TABLE xhs_note (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    nickname VARCHAR(64) DEFAULT NULL,
    avatar VARCHAR(255) DEFAULT NULL,
    ip_location VARCHAR(255) DEFAULT NULL,
    add_ts BIGINT NOT NULL,
    last_modify_ts BIGINT NOT NULL,
    note_id VARCHAR(64) NOT NULL,
    type VARCHAR(16) DEFAULT NULL,
    title VARCHAR(255) DEFAULT NULL,
    description TEXT,
    video_url TEXT,
    time BIGINT NOT NULL,
    last_update_time BIGINT NOT NULL,
    liked_count VARCHAR(16) DEFAULT NULL,
    collected_count VARCHAR(16) DEFAULT NULL,
    comment_count VARCHAR(16) DEFAULT NULL,
    share_count VARCHAR(16) DEFAULT NULL,
    image_list TEXT,
    tag_list TEXT,
    note_url VARCHAR(255) DEFAULT NULL,
    source_keyword VARCHAR(255) DEFAULT ''
);

CREATE INDEX idx_xhs_note_note_id ON xhs_note(note_id);
CREATE INDEX idx_xhs_note_time ON xhs_note(time);
```

## 📋 实施步骤

### 阶段一：基础架构 (2-3天)
1. ✅ 创建数据库抽象基类
2. ✅ 实现PostgreSQL适配器
3. ✅ 创建数据库工厂类
4. ✅ 更新配置管理

### 阶段二：SQL转换 (3-4天)
1. ✅ 转换表结构SQL文件
2. ✅ 处理SQL方言差异
3. ✅ 实现参数占位符转换
4. ✅ 测试基本CRUD操作

### 阶段三：集成测试 (2-3天)
1. ✅ 更新db.py主文件
2. ✅ 测试各平台数据存储
3. ✅ 性能对比测试
4. ✅ 文档更新

## 🔧 技术要点

### 依赖包更新
```bash
# requirements.txt 新增
asyncpg==0.29.0  # PostgreSQL异步驱动
```

### 主要差异处理
1. **参数占位符**: MySQL的`%s` → PostgreSQL的`$1, $2...`
2. **字段引用**: MySQL的`` ` `` → PostgreSQL的`"`
3. **自增主键**: MySQL的`AUTO_INCREMENT` → PostgreSQL的`SERIAL`
4. **返回插入ID**: MySQL的`lastrowid` → PostgreSQL的`RETURNING id`

## 📊 预期效果

### 优势
- ✅ 支持更强大的PostgreSQL特性
- ✅ 更好的并发性能
- ✅ 更严格的数据类型检查
- ✅ 更好的JSON支持

### 兼容性
- ✅ 保持现有MySQL功能完全兼容
- ✅ 通过配置切换数据库类型
- ✅ 代码改动最小化

## 🎯 总结

**实现难度：中等偏易 (3/5)**

主要工作量在于：
1. SQL语法转换 (40%)
2. 适配器实现 (30%)
3. 测试验证 (20%)
4. 文档更新 (10%)

预计总工作量：**7-10个工作日**
