#!/usr/bin/env python3
"""
创建 user_activity_logs 表
运行此脚本创建用户行为日志表
"""

import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import engine, Base

def create_activity_log_table():
    """创建 user_activity_logs 表"""
    print("开始创建 user_activity_logs 表...")
    
    try:
        # 导入模型（确保 UserActivityLog 被注册到 Base.metadata）
        from models import UserActivityLog
        
        # 创建所有表（已存在的会跳过）
        Base.metadata.create_all(bind=engine)
        
        print("[OK] 用户行为日志表创建成功！")
        
        # 验证表是否创建
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'user_activity_logs' in tables:
            print("[OK] user_activity_logs 表已存在于数据库中")
            
            # 显示表结构
            columns = inspector.get_columns('user_activity_logs')
            print(f"\n表结构（{len(columns)} 个字段）：")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        else:
            print("[ERROR] 表创建失败：user_activity_logs 不在数据库中")
            
    except Exception as e:
        print(f"[ERROR] 创建表失败: {str(e)}")
        raise

if __name__ == "__main__":
    create_activity_log_table()
