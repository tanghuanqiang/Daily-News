"""
添加用户脚本
用法: python -m scripts.add_user
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import User, Base
from passlib.context import CryptContext

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def add_user(email: str, password: str):
    """添加用户"""
    db: Session = SessionLocal()
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"用户 {email} 已存在!")
            return False
        
        # 创建新用户
        hashed_password = get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            email_notifications=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"用户创建成功!")
        print(f"  ID: {new_user.id}")
        print(f"  Email: {new_user.email}")
        print(f"  Created at: {new_user.created_at}")
        return True
        
    except Exception as e:
        print(f"创建用户失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # 要添加的用户信息
    email = "domtang12138@gmail.com"
    password = "123456"
    
    print(f"正在创建用户: {email}")
    add_user(email, password)
