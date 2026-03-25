#!/usr/bin/env python3
"""
验证所有路由文件是否可以正常导入
"""

import sys
import os
import traceback

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """测试所有路由文件的导入"""
    print("正在验证路由文件导入...")
    
    try:
        # 测试 auth.py
        from routes.auth import router as auth_router
        print("✓ routes.auth 导入成功")
        
        # 测试其他路由文件
        from routes import subscriptions, preferences, schedule, sharing
        print("✓ routes.__init__ 导入成功")
        
        # 测试所有路由
        from routes.subscriptions import router as subscriptions_router
        print("✓ routes.subscriptions 导入成功")
        
        from routes.preferences import router as preferences_router
        print("✓ routes.preferences 导入成功")
        
        from routes.schedule import router as schedule_router
        print("✓ routes.schedule 导入成功")
        
        from routes.sharing import router as sharing_router
        print("✓ routes.sharing 导入成功")
        
        print("\n✅ 所有路由文件导入成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ 导入失败: {str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
