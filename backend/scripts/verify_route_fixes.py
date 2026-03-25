#!/usr/bin/env python3
"""
验证路由修复脚本
测试所有修复的路由是否正常工作
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_endpoint(method, endpoint, data=None, token=None, description=""):
    """测试一个端点"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"URL: {method} {BASE_URL}{endpoint}")
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(f"{BASE_URL}{endpoint}", json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        
        print(f"状态码: {response.status_code}")
        if response.status_code in [200, 201]:
            print("✅ 成功")
            try:
                result = response.json()
                print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
            except:
                print(f"响应文本: {response.text[:200]}")
            return True
        else:
            print(f"❌ 失败: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


def main():
    print("="*60)
    print("路由修复验证测试")
    print(f"开始时间: {datetime.now()}")
    print("="*60)
    
    results = []
    token = None
    
    # 1. 测试 resend-verification 别名
    results.append(test_endpoint(
        "POST", "/api/auth/resend-verification",
        data={"email": "test@example.com"},
        description="1. 重发验证邮件别名 (/resend-verification)"
    ))
    
    # 2. 测试 verify-email 别名
    results.append(test_endpoint(
        "POST", 
        "/api/auth/verify-email",
        data={"email": "test@example.com", "code": "123456"},
        description="2. 验证邮箱别名 (/verify-email)"
    ))
    
    # 3. 测试 forgot-password 别名
    results.append(test_endpoint(
        "POST",
        "/api/auth/forgot-password",
        data={"email": "test@example.com"},
        description="3. 忘记密码别名 (/forgot-password)"
    ))
    
    # 4. 测试 reset-password (使用 verification_code 字段)
    results.append(test_endpoint(
        "POST",
        "/api/auth/reset-password",
        data={
            "email": "test@example.com",
            "verification_code": "123456",
            "new_password": "newpass123"
        },
        description="4. 重置密码 (verification_code字段)"
    ))
    
    # 需要先登录获取 token
    print("\n" + "="*60)
    print("登录获取 token...")
    try:
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "test123"},
            timeout=10
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            print("✅ 登录成功，获取到 token")
        else:
            print("⚠️  登录失败，部分测试需要 token 的将无法执行")
    except Exception as e:
        print(f"⚠️  登录异常: {e}")
    
    if token:
        # 5. 测试 profile 别名
        results.append(test_endpoint(
            "PUT",
            "/api/auth/profile?enabled=true",
            token=token,
            description="5. 更新用户配置别名 (/profile)"
        ))
        
        # 6. 测试 custom-feeds 别名
        results.append(test_endpoint(
            "GET",
            "/api/subscriptions/custom-feeds",
            token=token,
            description="6. 获取自定义订阅源别名 (/custom-feeds)"
        ))
        
        # 7. 测试 preferences 根路由别名
        results.append(test_endpoint(
            "GET",
            "/api/preferences/",
            token=token,
            description="7. 获取偏好设置根路由别名 (/preferences/)"
        ))
        
        # 8. 测试 hide-source 路由
        results.append(test_endpoint(
            "POST",
            "/api/preferences/hide-source?source=test-source",
            token=token,
            description="8. 隐藏来源路由 (/hide-source)"
        ))
        
        # 9. 测试 unhide-source 路由
        results.append(test_endpoint(
            "POST",
            "/api/preferences/unhide-source?source=test-source",
            token=token,
            description="9. 取消隐藏来源路由 (/unhide-source)"
        ))
        
        # 10. 测试 mark-read 别名
        results.append(test_endpoint(
            "POST",
            "/api/preferences/mark-read/1",
            token=token,
            description="10. 标记已读别名 (/mark-read/:id)"
        ))
        
        # 11. 测试 schedule 根路由别名
        results.append(test_endpoint(
            "GET",
            "/api/schedule/",
            token=token,
            description="11. 获取定时任务根路由别名 (/schedule/)"
        ))
        
        # 12. 测试 send-now 别名
        results.append(test_endpoint(
            "POST",
            "/api/schedule/send-now",
            token=token,
            description="12. 立即发送邮件别名 (/send-now)"
        ))
        
        # 13. 测试 share/generate JSON Body
        results.append(test_endpoint(
            "POST",
            "/api/share/generate",
            data={
                "news_id": 1,
                "platform": "wechat",
                "use_roast_mode": False
            },
            token=token,
            description="13. 生成分享内容 (JSON Body)"
        ))
    
    # 统计结果
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"总测试数: {total}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "通过率: N/A")
    
    if failed == 0 and total > 0:
        print("\n🎉 所有路由修复验证通过！")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查后端服务是否正常运行")
        return False


if __name__ == "__main__":
    main()
