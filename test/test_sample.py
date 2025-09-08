#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChecker Sample Tests

Simple tests to verify the test framework is working correctly.

Author: OpenChecker Team
"""

import unittest
import pytest
from unittest.mock import Mock, patch
import tempfile
import os
import shutil


class TestSample(unittest.TestCase):
    """示例测试类"""

    def setUp(self):
        """测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_basic_functionality(self):
        """测试基本功能"""
        # 基本断言
        self.assertTrue(True)
        self.assertEqual(1 + 1, 2)
        self.assertIn("test", "This is a test")

    def test_mock_usage(self):
        """测试Mock的使用"""
        mock_obj = Mock()
        mock_obj.return_value = "mocked"
        
        result = mock_obj()
        self.assertEqual(result, "mocked")
        mock_obj.assert_called_once()

    @patch('os.path.exists')
    def test_patch_decorator(self, mock_exists):
        """测试patch装饰器"""
        mock_exists.return_value = True
        
        result = os.path.exists("/fake/path")
        self.assertTrue(result)
        mock_exists.assert_called_once_with("/fake/path")

    def test_file_operations(self):
        """测试文件操作"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        
        # 写入文件
        with open(test_file, 'w') as f:
            f.write("Hello, OpenChecker!")
        
        # 验证文件存在
        self.assertTrue(os.path.exists(test_file))
        
        # 读取文件
        with open(test_file, 'r') as f:
            content = f.read()
        
        self.assertEqual(content, "Hello, OpenChecker!")

    def test_exception_handling(self):
        """测试异常处理"""
        with self.assertRaises(ValueError):
            raise ValueError("Test exception")
        
        with self.assertRaises(ZeroDivisionError):
            1 / 0

    @pytest.mark.unit
    def test_unit_marker(self):
        """带单元测试标记的测试"""
        self.assertEqual("unit", "unit")

    @pytest.mark.integration
    def test_integration_marker(self):
        """带集成测试标记的测试"""
        self.assertEqual("integration", "integration")


class TestPytestFeatures:
    """Pytest风格的测试类"""

    def test_simple_assertion(self):
        """简单断言测试"""
        assert 1 + 1 == 2
        assert "hello" in "hello world"

    def test_with_fixture(self, temp_directory):
        """使用夹具的测试"""
        assert os.path.exists(temp_directory)
        
        # 在临时目录中创建文件
        test_file = os.path.join(temp_directory, "pytest_test.txt")
        with open(test_file, 'w') as f:
            f.write("Pytest test content")
        
        assert os.path.exists(test_file)

    @pytest.mark.parametrize("input,expected", [
        (1, 1),
        (2, 4),
        (3, 9),
        (4, 16),
    ])
    def test_parametrized(self, input, expected):
        """参数化测试"""
        assert input ** 2 == expected

    @pytest.mark.unit
    def test_unit_pytest(self):
        """Pytest单元测试"""
        data = {"key": "value"}
        assert data["key"] == "value"

    @pytest.mark.integration
    def test_integration_pytest(self):
        """Pytest集成测试"""
        import json
        data = {"test": "integration"}
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert parsed == data


def test_standalone_function():
    """独立的测试函数"""
    assert True is True
    assert False is False


@pytest.mark.security
def test_security_example():
    """安全测试示例"""
    # 模拟安全检查
    sensitive_data = "password123"
    assert len(sensitive_data) > 8  # 密码长度检查


@pytest.mark.slow
def test_performance_example():
    """性能测试示例"""
    import time
    
    start_time = time.time()
    
    # 模拟一些处理
    result = sum(range(1000))
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 验证结果和性能
    assert result == 499500
    assert duration < 1.0  # 应该在1秒内完成


if __name__ == '__main__':
    # 可以用unittest运行
    unittest.main() 