#!/usr/bin/env python3
"""
添加 last_login 字段到 users 表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 从环境变量或默认配置获取数据库 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://tang:010123@localhost:15432/dailydigest"
)

# 创建数据库连接
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def add_last_login_column():
    """添加 last_login 列到 users 表"""
    db = SessionLocal()
    try:
        # 检查列是否已存在
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'last_login'
        """))
        
        if result.fetchone():
            print("✓ last_login 列已存在，无需添加")
            return
        
        # 添加列
        db.execute(text("""
            ALTER TABLE users 
            ADD COLUMN last_login TIMESTAMP NULL
        """))
        db.commit()
        print("✓ 成功添加 last_login 列到 users 表")
        
    except Exception as e:
        db.rollback()
        print(f"✗ 添加列失败: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("添加 last_login 字段到 users 表")
    print("=" * 60)
    
    try:
        add_last_login_column()
        print("\n✅ 数据库迁移完成！")
    except Exception as e:
        print(f"\n❌ 迁移失败: {str(e)}")
        sys.exit(1)
