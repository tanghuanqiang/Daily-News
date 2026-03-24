"""
数据库迁移脚本: 添加缺失的字段

这个脚本会检查并添加数据库中缺失的字段。

运行方法:
    # 在Docker容器内运行
    docker-compose exec backend python scripts/migrate_db.py
    
    # 或在本地运行
    cd backend
    python scripts/migrate_db.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine, SessionLocal
from datetime import datetime


def get_existing_columns(table_name: str) -> set:
    """获取表中已存在的字段"""
    db = SessionLocal()
    try:
        # PostgreSQL 查询字段信息
        query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name
        """)
        
        result = db.execute(query, {"table_name": table_name})
        columns = {row[0] for row in result.fetchall()}
        return columns
    finally:
        db.close()


def add_column_if_missing(table_name: str, column_name: str, column_definition: str):
    """如果字段不存在则添加"""
    existing_columns = get_existing_columns(table_name)
    
    if column_name in existing_columns:
        print(f"✅ {table_name}.{column_name} 字段已存在")
        return True
    
    db = SessionLocal()
    try:
        alter_query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
        db.execute(alter_query)
        db.commit()
        print(f"✅ 成功添加字段 {table_name}.{column_name}")
        return True
    except Exception as e:
        print(f"❌ 添加字段 {table_name}.{column_name} 失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def create_index_if_not_exists(table_name: str, index_name: str, index_definition: str):
    """创建索引(如果不存在)"""
    db = SessionLocal()
    try:
        index_query = text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {index_definition}")
        db.execute(index_query)
        db.commit()
        print(f"✅ 索引 {index_name} 已创建/已存在")
    except Exception as e:
        print(f"⚠️  创建索引 {index_name} 失败: {e}")
        db.rollback()
    finally:
        db.close()


def migrate_database():
    """执行数据库迁移"""
    
    print("=" * 70)
    print("开始数据库迁移...")
    print("=" * 70)
    
    migrations = [
        # (表名, 字段名, 字段定义)
        ("users", "username", "VARCHAR NULL UNIQUE"),
        ("users", "email_verified", "BOOLEAN DEFAULT FALSE"),
        ("users", "email_notifications", "BOOLEAN DEFAULT TRUE"),
        ("users", "email_schedule_enabled", "BOOLEAN DEFAULT FALSE"),
        ("users", "email_schedule_type", "VARCHAR DEFAULT 'daily'"),
        ("users", "email_schedule_hour", "INTEGER DEFAULT 9"),
        ("users", "email_schedule_minute", "INTEGER DEFAULT 0"),
        ("users", "email_schedule_day_of_week", "INTEGER DEFAULT 0"),
        ("users", "email_schedule_interval_hours", "INTEGER DEFAULT 24"),
        ("users", "last_email_sent_at", "TIMESTAMP NULL"),
    ]
    
    success_count = 0
    failed_count = 0
    
    for table_name, column_name, column_definition in migrations:
        if add_column_if_missing(table_name, column_name, column_definition):
            success_count += 1
        else:
            failed_count += 1
    
    # 创建索引
    print("\n创建索引...")
    create_index_if_not_exists("users", "ix_users_username", "(username)")
    create_index_if_not_exists("users", "ix_users_email", "(email)")
    
    print("\n" + "=" * 70)
    print(f"迁移完成! 成功: {success_count}, 失败: {failed_count}")
    print("=" * 70)
    
    return failed_count == 0


if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
