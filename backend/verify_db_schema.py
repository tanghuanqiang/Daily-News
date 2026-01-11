#!/usr/bin/env python3
"""
验证数据库表结构脚本

使用方法：
    python verify_db_schema.py
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import settings


def verify_schema():
    """验证数据库表结构"""
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
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查 custom_rss_feeds 表结构
        cursor.execute("PRAGMA table_info(custom_rss_feeds)")
        columns = cursor.fetchall()
        
        if not columns:
            print("custom_rss_feeds 表不存在")
            return
        
        print("\ncustom_rss_feeds 表结构:")
        print("-" * 60)
        print(f"{'列名':<20} {'类型':<15} {'非空':<8} {'默认值':<15}")
        print("-" * 60)
        
        has_roast_mode = False
        for col in columns:
            cid, name, col_type, notnull, default_val, pk = col
            notnull_str = "是" if notnull else "否"
            default_str = str(default_val) if default_val else "无"
            print(f"{name:<20} {col_type:<15} {notnull_str:<8} {default_str:<15}")
            if name == "roast_mode":
                has_roast_mode = True
        
        print("-" * 60)
        
        if has_roast_mode:
            print("\n[OK] roast_mode 字段已存在")
        else:
            print("\n[ERROR] roast_mode 字段不存在，需要运行迁移脚本")
            print("运行: python migrate_add_roast_mode.py")
        
    except sqlite3.Error as e:
        print(f"[ERROR] 查询失败: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("验证数据库表结构")
    print("=" * 60)
    verify_schema()
    print("\n验证完成！")
