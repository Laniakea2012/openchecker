import requests

"""
API测试脚本
功能：测试OpenChecker API的认证和基本功能

使用说明：
1. 通过认证接口获取访问令牌
2. 使用令牌访问受保护的API端点
"""

# ==================== API调用示例（curl命令） ====================
# 1. 获取访问令牌
# curl -X POST http://localhost:8083/auth \
#   -H "Content-Type: application/json" \
#   -d '{"username": "temporary_user", "password": "default_password"}'

# 2. 使用令牌访问受保护的路由
# curl -X POST http://localhost:8083/opencheck \
#   -H "Content-Type: application/json" \
#   -H "Authorization: Bearer <access_token>" \
#   -d '{
#     "commands": ["osv-scanner", "scancode"],
#     "project_url": "https://github.com/example/project",
#     "callback_url": "https://example.com/callback",
#     "task_metadata": {"priority": "high"}
#   }'

# ==================== Python实现 ====================

baseURL = 'http://localhost:8080/'

headers = {
    'Content-Type': 'application/json'
}

if __name__ == "__main__":
    authURL = baseURL + 'auth'
    
    authPayload = {
        'username': 'temporary_user',
        'password': 'default_password'
    }

    try:
        response = requests.post(url=authURL, headers=headers, json=authPayload)
    except Exception as e:
        print(e)
    else:
        # status_code = response.status_code
        resPayload = response.json()
        if 'access_token' in resPayload:
            access_token = response.json()['access_token']
            print(access_token)
        else:
            print(resPayload)
            exit()

    testURL = baseURL + 'test'
    headers['Authorization'] = 'Bearer' + ' ' + access_token
    payload = {
        "message": 'ping for test'
    }

    try:
        response = requests.post(url=testURL, headers=headers, json=payload)
    except Exception as e:
        print(e)
    else:
        # print(response)
        print(response.json())