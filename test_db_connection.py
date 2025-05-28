#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
"""

import asyncio
import os
from dotenv import load_dotenv
import aiomysql

# 加载环境变量
load_dotenv()

async def test_db_connection():
    """测试数据库连接"""
    
    # 从环境变量读取配置
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "db": os.getenv("DB_NAME", "media_crawler"),
        "charset": "utf8mb4"
    }
    
    print("=== 数据库连接测试 ===")
    print(f"配置信息:")
    print(f"  Host: {db_config['host']}")
    print(f"  Port: {db_config['port']}")
    print(f"  User: {db_config['user']}")
    print(f"  Password: {'*' * len(db_config['password']) if db_config['password'] else '(空)'}")
    print(f"  Database: {db_config['db']}")
    print()
    
    try:
        print("正在尝试连接数据库...")
        
        # 首先尝试连接到 MySQL 服务器（不指定数据库）
        conn = await aiomysql.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            charset=db_config["charset"]
        )
        
        print("✅ 成功连接到 MySQL 服务器!")
        
        # 检查数据库是否存在
        cursor = await conn.cursor()
        await cursor.execute("SHOW DATABASES LIKE %s", (db_config["db"],))
        result = await cursor.fetchone()
        
        if result:
            print(f"✅ 数据库 '{db_config['db']}' 存在")
        else:
            print(f"⚠️  数据库 '{db_config['db']}' 不存在，需要创建")
            
            # 创建数据库
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_config['db']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ 已创建数据库 '{db_config['db']}'")
        
        await cursor.close()
        conn.close()
        
        # 现在尝试连接到指定的数据库
        pool = await aiomysql.create_pool(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            db=db_config["db"],
            charset=db_config["charset"],
            autocommit=True
        )
        
        print(f"✅ 成功连接到数据库 '{db_config['db']}'!")
        
        # 测试查询
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT VERSION()")
                version = await cursor.fetchone()
                print(f"✅ MySQL 版本: {version[0]}")
        
        pool.close()
        await pool.wait_closed()
        
        print("\n🎉 数据库连接测试成功!")
        return True
        
    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        print("\n可能的解决方案:")
        print("1. 检查 MySQL 服务是否正在运行")
        print("2. 检查用户名和密码是否正确")
        print("3. 检查主机和端口是否正确")
        print("4. 检查用户是否有访问权限")
        return False

if __name__ == "__main__":
    asyncio.run(test_db_connection())
