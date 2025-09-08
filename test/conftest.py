#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChecker Test Configuration

This module provides pytest configuration, fixtures, and test environment setup
for the OpenChecker test suite.

Author: OpenChecker Team
"""

import pytest
import tempfile
import shutil
import os
import json
from unittest.mock import Mock, patch
import logging

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Mock the imports that might not be available during testing
try:
    from openchecker.main import app
except ImportError:
    # Create a mock Flask app for testing
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True

try:
    from openchecker.user_manager import User
except ImportError:
    # Create a mock User class
    class User:
        def __init__(self, user_id, username, password_hash):
            self.id = user_id
            self.username = username
            self.password_hash = password_hash


@pytest.fixture(scope="session")
def test_config():
    """测试配置夹具"""
    return {
        "OpenCheck": {
            "repos_dir": "/tmp/test_repos"
        },
        "RabbitMQ": {
            "host": "localhost",
            "port": 5672,
            "username": "test_user",
            "password": "test_password",
            "virtual_host": "/"
        },
        "SonarQube": {
            "host": "localhost",
            "port": "9000",
            "token": "test_sonar_token"
        },
        "JWT": {
            "secret_key": "test_secret_key",
            "expires_minutes": "30"
        }
    }


@pytest.fixture(scope="function")
def temp_directory():
    """临时目录夹具"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def test_repo_structure(temp_directory):
    """测试仓库结构夹具"""
    repo_path = os.path.join(temp_directory, "test_repo")
    os.makedirs(repo_path)
    
    # 创建基本文件结构
    files_to_create = {
        "README.md": "# Test Repository\n\nThis is a test repository.",
        "LICENSE": "MIT License\n\nCopyright (c) 2024",
        "setup.py": "from setuptools import setup\n\nsetup(name='test')",
        ".gitignore": "*.pyc\n__pycache__/\n.env",
        "requirements.txt": "flask==2.2.3\nrequests==2.26.0"
    }
    
    for filename, content in files_to_create.items():
        file_path = os.path.join(repo_path, filename)
        with open(file_path, 'w') as f:
            f.write(content)
    
    # 创建子目录
    src_dir = os.path.join(repo_path, "src")
    os.makedirs(src_dir)
    
    with open(os.path.join(src_dir, "main.py"), 'w') as f:
        f.write("def main():\n    print('Hello, World!')\n")
    
    # 创建GitHub工作流目录
    workflows_dir = os.path.join(repo_path, ".github", "workflows")
    os.makedirs(workflows_dir)
    
    workflow_content = """
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: github/codeql-action/analyze@v1
    """
    
    with open(os.path.join(workflows_dir, "ci.yml"), 'w') as f:
        f.write(workflow_content)
    
    return repo_path


@pytest.fixture(scope="function")
def flask_app():
    """Flask应用夹具"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    app.config['JWT_SECRET_KEY'] = 'test_jwt_secret'
    
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope="function")
def test_user():
    """测试用户夹具"""
    return User(
        user_id="test_user_123",
        username="test_user",
        password_hash="hashed_password"
    )


@pytest.fixture(scope="function")
def sample_message():
    """示例消息夹具"""
    return {
        "command_list": ["url-checker", "binary-checker", "security-policy-checker"],
        "project_url": "https://github.com/test/repo",
        "commit_hash": "abc123def456",
        "access_token": "github_token_123",
        "callback_url": "https://callback.example.com/webhook",
        "task_metadata": {
            "version_number": "1.0.0",
            "priority": "normal",
            "tags": ["security", "compliance"]
        }
    }


@pytest.fixture(scope="function")
def mock_rabbitmq_config():
    """模拟RabbitMQ配置夹具"""
    return {
        'host': 'localhost',
        'port': 5672,
        'username': 'guest',
        'password': 'guest',
        'virtual_host': '/'
    }


@pytest.fixture(scope="function")
def mock_platform_adapter():
    """模拟平台适配器夹具"""
    mock_adapter = Mock()
    mock_adapter.get_platform_name.return_value = "github"
    mock_adapter.is_valid_project_url.return_value = True
    mock_adapter.download_project_source.return_value = (True, "")
    mock_adapter.get_file_content.return_value = ("file content", None)
    mock_adapter.parse_project_url.return_value = ("owner", "repo")
    return mock_adapter


@pytest.fixture(scope="function")
def sample_workflow_files():
    """示例工作流文件夹具"""
    return {
        "security.yml": """
name: Security Analysis
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v2
      - uses: github/codeql-action/analyze@v1
        with:
          languages: python, javascript
      - uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        """,
        
        "ci.yml": """
name: Continuous Integration
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Run tests
        run: python -m pytest
        """,
        
        "dangerous.yml": """
name: Dangerous Workflow
on:
  pull_request_target:
    types: [opened]
jobs:
  dangerous:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - name: Run untrusted code
        run: |
          echo "This could be dangerous"
          eval "${{ github.event.pull_request.title }}"
        """
    }


@pytest.fixture(scope="function")
def sample_check_results():
    """示例检查结果夹具"""
    return {
        "scan_results": {
            "url-checker": {
                "valid": True,
                "platform": "github",
                "accessibility": "public"
            },
            "binary-checker": {
                "binary_files": [],
                "archive_files": ["data.zip"],
                "total_files": 15
            },
            "security-policy-checker": {
                "has_security_policy": True,
                "security_files": ["SECURITY.md"],
                "policy_score": 85
            },
            "sast-checker": {
                "tools_detected": ["codeql", "snyk"],
                "coverage_score": 70,
                "workflows_analyzed": 2
            }
        },
        "metadata": {
            "scan_duration": 45.2,
            "timestamp": "2024-01-01T12:00:00Z",
            "version": "1.0.0"
        }
    }


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """自动清理日志器夹具"""
    yield
    # 测试后清理所有openchecker相关的日志器
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith('openchecker'):
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)


@pytest.fixture(scope="function")
def mock_sonar_response():
    """模拟SonarQube响应夹具"""
    return {
        "component": {
            "key": "test_project",
            "name": "Test Project",
            "qualifier": "TRK"
        },
        "measures": [
            {
                "metric": "bugs",
                "value": "5"
            },
            {
                "metric": "vulnerabilities", 
                "value": "2"
            },
            {
                "metric": "code_smells",
                "value": "12"
            },
            {
                "metric": "coverage",
                "value": "78.5"
            }
        ]
    }


@pytest.fixture(scope="function") 
def security_policy_content():
    """安全策略内容夹具"""
    return """
# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please send an email to security@example.com.
Please include the following information:

- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if available)

## Supported Versions

We actively support the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.1.x   | :white_check_mark: |
| 2.0.x   | :white_check_mark: |
| 1.9.x   | :x:                |

## Security Response Process

1. We will acknowledge receipt of your vulnerability report within 24 hours.
2. Our security team will investigate and confirm the vulnerability.
3. We will develop and test a fix.
4. We will coordinate disclosure with you.

## Security Best Practices

- Keep your dependencies up to date
- Use strong authentication mechanisms  
- Follow the principle of least privilege
- Regularly audit your code for security issues
"""


# pytest配置
def pytest_configure(config):
    """pytest配置函数"""
    # 设置测试标记
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


def pytest_collection_modifyitems(config, items):
    """修改收集到的测试项"""
    # 为没有标记的测试添加默认标记
    for item in items:
        # 如果测试名包含"integration"，添加integration标记
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        # 如果测试名包含"slow"，添加slow标记  
        elif "slow" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        # 默认添加unit标记
        else:
            item.add_marker(pytest.mark.unit)


# 测试会话开始时的设置
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 设置环境变量
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    yield
    
    # 清理环境变量
    if 'TESTING' in os.environ:
        del os.environ['TESTING']
    if 'LOG_LEVEL' in os.environ:
        del os.environ['LOG_LEVEL']


# 错误处理夹具
@pytest.fixture
def capture_logs():
    """捕获日志输出夹具"""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    logger = logging.getLogger('openchecker')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    logger.removeHandler(handler) 