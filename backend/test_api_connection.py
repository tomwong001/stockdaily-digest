#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试后端 API 连接和认证"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("1. 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"   ✅ 状态码: {response.status_code}")
        print(f"   ✅ 响应: {response.json()}")
        return True
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False

def test_auth():
    """测试认证（需要先注册一个测试用户）"""
    print("\n2. 测试认证...")
    test_email = "test@example.com"
    test_password = "test123456"
    
    # 先尝试登录
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_email, "password": test_password}
        )
        if response.status_code == 200:
            token = response.json()["token"]
            print(f"   ✅ 登录成功")
            return token
        else:
            print(f"   ⚠️  登录失败，尝试注册...")
    except Exception as e:
        print(f"   ⚠️  登录请求失败: {e}")
    
    # 如果登录失败，尝试注册
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": test_email, "password": test_password, "name": "Test User"}
        )
        if response.status_code == 200:
            token = response.json()["token"]
            print(f"   ✅ 注册成功")
            return token
        else:
            print(f"   ❌ 注册失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ 注册请求失败: {e}")
        return None

def test_user_companies(token):
    """测试获取用户关注的公司列表"""
    print("\n3. 测试获取用户关注的公司列表...")
    if not token:
        print("   ⚠️  跳过（无 token）")
        return
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/user/companies", headers=headers)
        print(f"   ✅ 状态码: {response.status_code}")
        if response.status_code == 200:
            companies = response.json()
            print(f"   ✅ 返回 {len(companies)} 家公司")
            if companies:
                print(f"   ✅ 示例: {companies[0]}")
        else:
            print(f"   ❌ 错误: {response.text}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")

def test_search_companies(token):
    """测试搜索公司"""
    print("\n4. 测试搜索公司...")
    if not token:
        print("   ⚠️  跳过（无 token）")
        return
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/companies/search?q=AAPL",
            headers=headers
        )
        print(f"   ✅ 状态码: {response.status_code}")
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ 返回 {len(results)} 个结果")
            if results:
                print(f"   ✅ 示例: {results[0]}")
        else:
            print(f"   ❌ 错误: {response.text}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("后端 API 连接测试")
    print("=" * 60)
    
    # 测试健康检查
    if not test_health():
        print("\n❌ 后端服务可能未启动，请检查:")
        print("   1. 后端是否在运行: python backend/main.py")
        print("   2. 端口 8000 是否被占用")
        exit(1)
    
    # 测试认证
    token = test_auth()
    
    # 测试需要认证的 API
    if token:
        test_user_companies(token)
        test_search_companies(token)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n如果测试失败，请检查:")
    print("1. 后端服务是否正常运行 (http://localhost:8000)")
    print("2. 数据库是否正常连接")
    print("3. 前端是否配置了正确的代理 (vite.config.ts)")

