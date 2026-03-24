#!/usr/bin/env python3
"""
管理员面板快速设置脚本
用于创建第一个管理员账户和测试管理员功能
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal, engine
from models import User, Base
from auth import get_password_hash
import getpass

def create_admin_account():
    """创建管理员账户"""
    db = SessionLocal()
    
    try:
        # 检查是否已存在管理员
        existing_admin = db.query(User).filter(User.is_admin == True).first()
        
        if existing_admin:
            print(f"✅ 已存在管理员账户: {existing_admin.email}")
            print(f"   用户名: {existing_admin.username or '未设置'}")
            return existing_admin
        
        print("=" * 60)
        print("创建管理员账户")
        print("=" * 60)
        
        # 获取管理员信息
        email = input("请输入管理员邮箱: ").strip()
        username = input("请输入管理员用户名 (可选): ").strip() or None
        password = getpass.getpass("请输入管理员密码: ")
        
        if not password:
            print("❌ 密码不能为空")
            return None
        
        # 确认密码
        confirm_password = getpass.getpass("请再次输入密码: ")
        if password != confirm_password:
            print("❌ 两次输入的密码不一致")
            return None
        
        # 检查邮箱是否已存在
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            # 更新为管理员
            existing_user.is_admin = True
            existing_user.username = username or existing_user.username
            if password:
                existing_user.hashed_password = get_password_hash(password)
            db.commit()
            print(f"✅ 成功将现有用户升级为管理员: {email}")
            return existing_user
        else:
            # 创建新管理员
            admin_user = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(password),
                is_admin=True,
                is_active=True,
                email_verified=True,
                email_notifications=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"✅ 管理员账户创建成功!")
            print(f"   邮箱: {email}")
            print(f"   用户名: {username or '未设置'}")
            return admin_user
            
    except Exception as e:
        print(f"❌ 创建管理员账户失败: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def list_all_users():
    """列出所有用户"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("\n" + "=" * 60)
        print("用户列表")
        print("=" * 60)
        print(f"{'ID':<5} {'邮箱':<25} {'用户名':<15} {'管理员':<8} {'活跃':<6}")
        print("-" * 60)
        for user in users:
            print(f"{user.id:<5} {user.email:<25} {user.username or '-':<15} "
                  f"{'是' if user.is_admin else '否':<8} {'是' if user.is_active else '否':<6}")
        print(f"\n总计: {len(users)} 个用户")
    finally:
        db.close()

def setup_database():
    """设置数据库"""
    print("=" * 60)
    print("设置数据库")
    print("=" * 60)
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
        
        # 检查User表是否有新字段
        db = SessionLocal()
        try:
            # 测试查询
            result = db.execute("SELECT COUNT(*) FROM users").scalar()
            print(f"✅ 数据库连接正常，现有 {result} 个用户")
        except Exception as e:
            print(f"⚠️  数据库检查: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 数据库设置失败: {e}")
        return False
    
    return True

def test_admin_api():
    """测试管理员API"""
    import requests
    
    print("\n" + "=" * 60)
    print("测试管理员API")
    print("=" * 60)
    
    try:
        # 测试概览API
        response = requests.get('http://localhost:8000/api/admin/overview')
        if response.status_code == 200:
            data = response.json()
            print("✅ API /api/admin/overview 测试成功")
            print(f"   用户总数: {data['users']['total']}")
            print(f"   活跃率: {data['users']['active_rate']}%")
        else:
            print(f"❌ API测试失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"❌ API连接失败: {e}")
        print("   请确保后端服务已启动: python main.py")

def show_admin_panel_url():
    """显示管理员面板访问地址"""
    print("\n" + "=" * 60)
    print("管理员面板访问信息")
    print("=" * 60)
    print("📊 管理员面板: http://localhost:5173/admin")
    print("📖 API文档: http://localhost:8000/docs")
    print("🛡️  导航栏图标: 紫色盾牌 (仅管理员可见)")
    print("\n💡 提示:")
    print("   1. 先启动后端: python main.py")
    print("   2. 启动前端: npm run dev (在frontend目录)")
    print("   3. 登录管理员账户")
    print("   4. 点击导航栏紫色盾牌图标")

def main():
    """主函数"""
    print("🚀 Daily-News 管理员面板设置脚本")
    print("=" * 60)
    
    # 步骤1: 设置数据库
    if not setup_database():
        print("❌ 数据库设置失败，请检查配置")
        return
    
    # 步骤2: 显示用户列表
    list_all_users()
    
    # 步骤3: 创建管理员账户
    admin = create_admin_account()
    
    if admin:
        print(f"\n✅ 管理员设置完成!")
        print(f"   登录邮箱: {admin.email}")
        print(f"   管理员权限: {'已启用' if admin.is_admin else '未启用'}")
    else:
        print("\n❌ 管理员账户创建失败")
    
    # 步骤4: 测试API
    print("\n" + "=" * 60)
    input("按Enter键测试API（确保后端已启动）...")
    test_admin_api()
    
    # 步骤5: 显示访问信息
    show_admin_panel_url()
    
    print("\n" + "=" * 60)
    print("🎉 设置完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
