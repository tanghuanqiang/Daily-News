#!/usr/bin/env python3
"""
数据库迁移脚本：为 NewsCache 表添加 entry_id 字段

使用方法：
    python migrate_add_entry_id.py

或者：
    cd backend
    python migrate_add_entry_id.py
"""

import sqlite3
import sys
from pathlib import Path

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
    
    if not db_path.startswith("/") and ":" not in db_path[:2]:
        backend_path = Path(__file__).parent / db_path
        if backend_path.exists():
            db_path = str(backend_path)
        else:
            project_root = Path(__file__).parent.parent
            db_path = str(project_root / db_path)
    
    print(f"正在连接数据库: {db_path}")
    
    if not Path(db_path).exists():
        print(f"数据库文件不存在: {db_path}")
        print("将在首次启动应用时自动创建数据库表。")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='news_cache'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("news_cache 表不存在，将在首次启动应用时自动创建。")
            conn.close()
            return
        
        # 检查列是否已存在
        if check_column_exists(cursor, "news_cache", "entry_id"):
            print("[OK] entry_id 列已存在，无需迁移。")
            conn.close()
            return
        
        # SQLite 不支持直接添加 UNIQUE 约束到现有列
        # 先添加列，然后在应用层面保证唯一性
        print("正在添加 entry_id 列...")
        cursor.execute("""
            ALTER TABLE news_cache 
            ADD COLUMN entry_id VARCHAR
        """)
        
        # 创建索引（不是唯一索引，因为SQLite在ALTER TABLE时无法直接添加唯一约束）
        print("正在创建 entry_id 索引...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_news_cache_entry_id 
                ON news_cache(entry_id)
            """)
        except sqlite3.OperationalError as e:
            # 索引可能已存在，忽略错误
            if "already exists" not in str(e).lower():
                raise
        
        conn.commit()
        print("[OK] 成功添加 entry_id 列和索引！")
        print("  注意：entry_id 的唯一性由应用层保证")
        
    except sqlite3.Error as e:
        print(f"[ERROR] 迁移失败: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("数据库迁移：添加 entry_id 字段")
    print("=" * 50)
    print()
    
    migrate_database()
    
    print()
    print("迁移完成！")
