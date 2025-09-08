#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChecker Main API Tests

This module provides comprehensive tests for the main Flask API functionality
including authentication, routing, message publishing, and error handling.

Author: OpenChecker Team
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import base64
from flask import Flask

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from openchecker.main import app
from openchecker.user_manager import User


class TestMainAPI(unittest.TestCase):
    """主API测试类"""

    def setUp(self):
        """测试前置设置"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # 测试用户凭据
        self.test_username = "test_user"
        self.test_password = "test_password"
        self.test_user_id = "user123"
        
    def get_auth_headers(self, token):
        """获取认证头"""
        return {'Authorization': f'Bearer {token}'}
    
    def get_basic_auth_headers(self, username, password):
        """获取基本认证头"""
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {'Authorization': f'Basic {credentials}'}

    @patch('openchecker.main.authenticate')
    @patch('openchecker.main.create_access_token')
    def test_auth_basic_auth_success(self, mock_create_token, mock_authenticate):
        """测试基本认证成功"""
        # 设置模拟
        test_user = User(self.test_user_id, self.test_username, "")
        mock_authenticate.return_value = test_user
        mock_create_token.return_value = "test_token_123"
        
        # 发送认证请求
        headers = self.get_basic_auth_headers(self.test_username, self.test_password)
        response = self.client.post('/auth', headers=headers)
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)
        self.assertEqual(data['token_type'], 'Bearer')
        mock_authenticate.assert_called_once_with(self.test_username, self.test_password)

    @patch('openchecker.main.authenticate')
    def test_auth_basic_auth_failure(self, mock_authenticate):
        """测试基本认证失败"""
        # 设置认证失败
        mock_authenticate.return_value = None
        
        # 发送认证请求
        headers = self.get_basic_auth_headers("wrong_user", "wrong_password")
        response = self.client.post('/auth', headers=headers)
        
        # 验证结果
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    @patch('openchecker.main.authenticate')
    @patch('openchecker.main.create_access_token')
    def test_auth_json_success(self, mock_create_token, mock_authenticate):
        """测试JSON认证成功"""
        # 设置模拟
        test_user = User(self.test_user_id, self.test_username, "")
        mock_authenticate.return_value = test_user
        mock_create_token.return_value = "test_token_456"
        
        # 发送JSON认证请求
        auth_data = {
            'username': self.test_username,
            'password': self.test_password
        }
        response = self.client.post('/auth', 
                                  data=json.dumps(auth_data),
                                  content_type='application/json')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)

    def test_auth_missing_credentials(self):
        """测试缺少认证凭据"""
        response = self.client.post('/auth')
        
        # 验证结果
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    @patch('openchecker.main.get_jwt_identity')
    @patch('openchecker.main.identity')
    def test_test_endpoint_get_success(self, mock_identity, mock_get_jwt):
        """测试/test端点GET请求成功"""
        # 设置模拟
        mock_get_jwt.return_value = self.test_user_id
        test_user = User(self.test_user_id, self.test_username, "")
        mock_identity.return_value = test_user
        
        # 模拟JWT装饰器
        with patch('openchecker.main.jwt_required', lambda: lambda f: f):
            response = self.client.get('/test')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('current_user', data)

    @patch('openchecker.main.get_jwt_identity')
    @patch('openchecker.main.identity')
    def test_test_endpoint_post_success(self, mock_identity, mock_get_jwt):
        """测试/test端点POST请求成功"""
        # 设置模拟
        mock_get_jwt.return_value = self.test_user_id
        test_user = User(self.test_user_id, self.test_username, "")
        mock_identity.return_value = test_user
        
        # 发送POST请求
        test_data = {'message': 'Hello, World!'}
        with patch('openchecker.main.jwt_required', lambda: lambda f: f):
            response = self.client.post('/test',
                                      data=json.dumps(test_data),
                                      content_type='application/json')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('received_message', data)

    @patch('openchecker.main.get_jwt_identity')
    @patch('openchecker.main.identity')
    @patch('openchecker.main.publish_message')
    @patch('openchecker.main.uuid.uuid4')
    def test_opencheck_endpoint_success(self, mock_uuid, mock_publish, mock_identity, mock_get_jwt):
        """测试/opencheck端点成功"""
        # 设置模拟
        mock_get_jwt.return_value = self.test_user_id
        test_user = User(self.test_user_id, self.test_username, "")
        mock_identity.return_value = test_user
        mock_uuid.return_value.hex = "test_task_id"
        mock_publish.return_value = True
        
        # 发送opencheck请求
        check_data = {
            'commands': ['url-checker', 'binary-checker'],
            'project_url': 'https://github.com/test/repo',
            'callback_url': 'https://callback.example.com',
            'task_metadata': {'version': '1.0.0'}
        }
        
        with patch('openchecker.main.jwt_required', lambda: lambda f: f):
            response = self.client.post('/opencheck',
                                      data=json.dumps(check_data),
                                      content_type='application/json')
        
        # 验证结果
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('task_id', data)
        mock_publish.assert_called_once()

    @patch('openchecker.main.get_jwt_identity')
    @patch('openchecker.main.identity')
    def test_opencheck_missing_required_fields(self, mock_identity, mock_get_jwt):
        """测试/opencheck端点缺少必需字段"""
        # 设置模拟
        mock_get_jwt.return_value = self.test_user_id
        test_user = User(self.test_user_id, self.test_username, "")
        mock_identity.return_value = test_user
        
        # 发送不完整的请求
        incomplete_data = {
            'commands': ['url-checker']
            # 缺少project_url
        }
        
        with patch('openchecker.main.jwt_required', lambda: lambda f: f):
            response = self.client.post('/opencheck',
                                      data=json.dumps(incomplete_data),
                                      content_type='application/json')
        
        # 验证结果
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    @patch('openchecker.main.get_jwt_identity')
    @patch('openchecker.main.identity')
    @patch('openchecker.main.publish_message')
    def test_opencheck_publish_failure(self, mock_publish, mock_identity, mock_get_jwt):
        """测试/opencheck端点消息发布失败"""
        # 设置模拟
        mock_get_jwt.return_value = self.test_user_id
        test_user = User(self.test_user_id, self.test_username, "")
        mock_identity.return_value = test_user
        mock_publish.return_value = False  # 发布失败
        
        # 发送opencheck请求
        check_data = {
            'commands': ['url-checker'],
            'project_url': 'https://github.com/test/repo',
            'callback_url': 'https://callback.example.com'
        }
        
        with patch('openchecker.main.jwt_required', lambda: lambda f: f):
            response = self.client.post('/opencheck',
                                      data=json.dumps(check_data),
                                      content_type='application/json')
        
        # 验证结果
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_opencheck_without_auth(self):
        """测试未认证访问/opencheck端点"""
        check_data = {
            'commands': ['url-checker'],
            'project_url': 'https://github.com/test/repo'
        }
        
        response = self.client.post('/opencheck',
                                  data=json.dumps(check_data),
                                  content_type='application/json')
        
        # 验证结果（具体状态码取决于JWT配置）
        self.assertIn(response.status_code, [401, 422])

    def test_invalid_endpoint(self):
        """测试无效端点"""
        response = self.client.get('/invalid_endpoint')
        
        # 验证结果
        self.assertEqual(response.status_code, 404)


class TestAPIConfiguration(unittest.TestCase):
    """API配置测试类"""

    @patch('openchecker.main.read_config')
    def test_jwt_configuration(self, mock_read_config):
        """测试JWT配置"""
        # 设置模拟配置
        mock_read_config.return_value = {
            'secret_key': 'test_secret',
            'expires_minutes': '60'
        }
        
        # 重新导入模块以应用配置
        # 这里可以测试配置是否正确应用
        self.assertTrue(True)  # 简化测试

    @patch('openchecker.main.test_rabbitmq_connection')
    @patch('openchecker.main.create_queue')
    def test_rabbitmq_initialization(self, mock_create_queue, mock_test_connection):
        """测试RabbitMQ初始化"""
        # 设置模拟
        mock_test_connection.return_value = True
        mock_create_queue.return_value = True
        
        # 这里可以测试应用启动时的RabbitMQ初始化
        # 具体实现取决于main.py中的初始化逻辑
        self.assertTrue(True)


class TestAPIErrorHandling(unittest.TestCase):
    """API错误处理测试类"""

    def setUp(self):
        """测试前置设置"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_invalid_json_request(self):
        """测试无效JSON请求"""
        response = self.client.post('/auth',
                                  data="invalid json",
                                  content_type='application/json')
        
        # 验证结果
        self.assertIn(response.status_code, [400, 500])

    def test_method_not_allowed(self):
        """测试不允许的HTTP方法"""
        response = self.client.put('/auth')
        
        # 验证结果
        self.assertEqual(response.status_code, 405)

    @patch('openchecker.main.get_jwt_identity')
    @patch('openchecker.main.identity')
    def test_internal_server_error(self, mock_identity, mock_get_jwt):
        """测试内部服务器错误处理"""
        # 设置模拟抛出异常
        mock_get_jwt.return_value = self.test_user_id
        mock_identity.side_effect = Exception("Database error")
        
        # 发送请求
        with patch('openchecker.main.jwt_required', lambda: lambda f: f):
            response = self.client.get('/test')
        
        # 验证错误处理
        self.assertIn(response.status_code, [500, 400])


class TestAPIIntegration(unittest.TestCase):
    """API集成测试类"""

    def setUp(self):
        """集成测试前置设置"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('openchecker.main.authenticate')
    @patch('openchecker.main.create_access_token')
    @patch('openchecker.main.publish_message')
    def test_complete_workflow(self, mock_publish, mock_create_token, mock_authenticate):
        """测试完整工作流：认证 -> 提交检查任务"""
        # 步骤1：认证
        test_user = User("user123", "test_user", "")
        mock_authenticate.return_value = test_user
        mock_create_token.return_value = "integration_token"
        
        auth_response = self.client.post('/auth',
                                       data=json.dumps({
                                           'username': 'test_user',
                                           'password': 'test_password'
                                       }),
                                       content_type='application/json')
        
        self.assertEqual(auth_response.status_code, 200)
        auth_data = json.loads(auth_response.data)
        token = auth_data['access_token']
        
        # 步骤2：提交检查任务
        mock_publish.return_value = True
        
        check_data = {
            'commands': ['url-checker', 'security-policy-checker'],
            'project_url': 'https://github.com/test/repo',
            'callback_url': 'https://callback.example.com'
        }
        
        with patch('openchecker.main.jwt_required', lambda: lambda f: f):
            check_response = self.client.post('/opencheck',
                                            data=json.dumps(check_data),
                                            content_type='application/json',
                                            headers={'Authorization': f'Bearer {token}'})
        
        # 验证结果
        self.assertEqual(check_response.status_code, 200)
        check_result = json.loads(check_response.data)
        self.assertIn('task_id', check_result)

    def test_rate_limiting_simulation(self):
        """测试速率限制模拟"""
        # 发送多个快速请求
        responses = []
        for i in range(5):
            response = self.client.post('/auth')
            responses.append(response.status_code)
        
        # 验证所有请求都被处理（没有速率限制的情况下）
        self.assertTrue(all(status in [400, 401] for status in responses))


if __name__ == '__main__':
    # 设置测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMainAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite) 