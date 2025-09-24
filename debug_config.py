#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试配置加载
"""

import os
from dotenv import load_dotenv

print("=== 调试配置加载 ===")

# 1. 检查 .env 文件是否存在
if os.path.exists('.env'):
    print("✅ .env 文件存在")
else:
    print("❌ .env 文件不存在")

# 2. 加载环境变量前
print("\n--- 加载环境变量前 ---")
print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD', 'NOT_SET')}")

# 3. 加载环境变量
load_dotenv()
print("\n--- 加载环境变量后 ---")
print(f"DB_HOST: {os.getenv('DB_HOST', 'NOT_SET')}")
print(f"DB_PORT: {os.getenv('DB_PORT', 'NOT_SET')}")
print(f"DB_USER: {os.getenv('DB_USER', 'NOT_SET')}")
print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD', 'NOT_SET')}")
print(f"DB_NAME: {os.getenv('DB_NAME', 'NOT_SET')}")

# 4. 导入配置模块
print("\n--- 导入配置模块 ---")
from config.db_config import DB_CONFIG

print("DB_CONFIG:")
for key, value in DB_CONFIG.items():
    if key == 'password':
        print(f"  {key}: {'*' * len(str(value)) if value else '(空)'}")
    else:
        print(f"  {key}: {value}")

# 5. 检查具体的环境变量值
print("\n--- 详细检查 ---")
db_password = os.getenv("DB_PASSWORD", "")
print(f"DB_PASSWORD 长度: {len(db_password)}")
print(f"DB_PASSWORD 是否为空: {db_password == ''}")
print(f"DB_PASSWORD 原始值: '{db_password}'")
