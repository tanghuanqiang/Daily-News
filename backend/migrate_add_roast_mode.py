#!/usr/bin/env python3
"""
数据库迁移脚本：为 CustomRSSFeed 表添加 roast_mode 字段

使用方法：
    python migrate_add_roast_mode.py

或者：
    cd backend
    python migrate_add_roast_mode.py
"""

import sqlite3
import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from database import settings


def check_column_exists(cursor, table_name, column_name):
    """检查表中是否存在指定列"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_database():
    """执行数据库迁移"""
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    
    # 如果是相对路径，需要找到数据库文件
    if not os.path.isabs(db_path):
        # 尝试在backend目录下
        backend_path = Path(__file__).parent / db_path
        if backend_path.exists():
            db_path = str(backend_path)
        else:
            # 尝试在项目根目录
            project_root = Path(__file__).parent.parent
            db_path = str(project_root / db_path)
    
    print(f"正在连接数据库: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        print("将在首次启动应用时自动创建数据库表。")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='custom_rss_feeds'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("custom_rss_feeds 表不存在，将在首次启动应用时自动创建。")
            conn.close()
            return
        
        # 检查列是否已存在
        if check_column_exists(cursor, "custom_rss_feeds", "roast_mode"):
            print("[OK] roast_mode 列已存在，无需迁移。")
            conn.close()
            return
        
        # 添加新列
        print("正在添加 roast_mode 列...")
        cursor.execute("""
            ALTER TABLE custom_rss_feeds 
            ADD COLUMN roast_mode BOOLEAN NOT NULL DEFAULT 0
        """)
        
        conn.commit()
        print("[OK] 成功添加 roast_mode 列！")
        print("  所有现有记录将默认设置为 roast_mode = False (正常模式)")
        
    except sqlite3.Error as e:
        print(f"[ERROR] 迁移失败: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("数据库迁移：添加 roast_mode 字段")
    print("=" * 50)
    print()
    
    migrate_database()
    
    print()
    print("迁移完成！")
