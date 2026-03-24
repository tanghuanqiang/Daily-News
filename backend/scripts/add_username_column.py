"""
添加 username 字段到 users 表

这个脚本用于在现有的数据库中添加 username 字段。
如果数据库是从旧版本迁移过来的,可能缺少这个字段。

运行方法:
    cd backend
    python scripts/add_username_column.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine, SessionLocal
from datetime import datetime


def add_username_column():
    """添加 username 字段到 users 表"""
    
    db = SessionLocal()
    
    try:
        # 检查字段是否已存在
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='username'
        """)
        
        result = db.execute(check_query).fetchone()
        
        if result:
            print("✅ username 字段已存在,无需添加")
            return
        
        # 添加 username 字段
        alter_query = text("""
            ALTER TABLE users 
            ADD COLUMN username VARCHAR NULL UNIQUE
        """)
        
        db.execute(alter_query)
        db.commit()
        
        print("✅ 成功添加 username 字段到 users 表")
        
        # 创建索引
        index_query = text("""
            CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)
        """)
        
        db.execute(index_query)
        db.commit()
        
        print("✅ 成功创建 username 索引")
        
    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("添加 username 字段到 users 表")
    print("=" * 60)
    
    add_username_column()
    
    print("\n✅ 数据库迁移完成!")
    print("\n提示: username 字段已设置为可选(nullable=True)")
    print("现有用户的 username 字段值为 NULL,可以通过管理后台设置")
