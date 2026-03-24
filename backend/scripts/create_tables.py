#!/usr/bin/env python3
"""
创建数据库表脚本
运行此脚本将创建所有模型对应的数据库表
"""

import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# 导入所有模型（这会注册模型到Base.metadata）
import models
from database import engine, Base

def create_tables():
    """创建所有数据库表"""
    print("开始创建数据库表...")
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("[OK] 数据库表创建成功！")
        
        # 列出所有创建的表
        print("\n已创建的表:")
        for table_name in sorted(Base.metadata.tables.keys()):
            print(f"  - {table_name}")
        
    except Exception as e:
        print(f"[ERROR] 创建数据库表失败: {str(e)}")
        raise

if __name__ == "__main__":
    create_tables()
