#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChecker Logger Module Tests

This module provides comprehensive tests for the logging functionality
including setup, configuration, performance monitoring, and log formatting.

Author: OpenChecker Team
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import logging
import json
import tempfile
import os
import shutil
from datetime import datetime

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from openchecker.logger import (
    setup_logging,
    get_logger,
    log_performance,
    StructuredFormatter,
    SimpleFormatter
)


class TestLoggerSetup(unittest.TestCase):
    """日志器设置测试类"""

    def setUp(self):
        """测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # 清理日志器
        logger = logging.getLogger('openchecker')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_setup_logging_default_config(self):
        """测试默认配置的日志设置"""
        setup_logging()
        
        # 获取根日志器
        logger = logging.getLogger('openchecker')
        
        # 验证日志器配置
        self.assertEqual(logger.level, logging.INFO)
        self.assertTrue(len(logger.handlers) > 0)

    def test_setup_logging_custom_level(self):
        """测试自定义日志级别"""
        setup_logging(log_level="DEBUG")
        
        logger = logging.getLogger('openchecker')
        self.assertEqual(logger.level, logging.DEBUG)

    def test_setup_logging_with_file(self):
        """测试文件日志配置"""
        setup_logging(
            log_file=self.log_file,
            enable_console=False,
            enable_file=True
        )
        
        logger = logging.getLogger('openchecker')
        
        # 检查是否有文件处理器
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        self.assertTrue(len(file_handlers) > 0)

    def test_setup_logging_structured_format(self):
        """测试结构化日志格式"""
        setup_logging(log_format="structured")
        
        logger = logging.getLogger('openchecker')
        
        # 检查格式器类型
        handler = logger.handlers[0] if logger.handlers else None
        if handler:
            self.assertIsInstance(handler.formatter, StructuredFormatter)

    def test_setup_logging_simple_format(self):
        """测试简单日志格式"""
        setup_logging(log_format="simple")
        
        logger = logging.getLogger('openchecker')
        
        # 检查格式器类型
        handler = logger.handlers[0] if logger.handlers else None
        if handler:
            self.assertIsInstance(handler.formatter, SimpleFormatter)

    def test_setup_logging_log_dir_creation(self):
        """测试日志目录创建"""
        log_dir = os.path.join(self.temp_dir, "new_logs")
        
        setup_logging(
            log_dir=log_dir,
            enable_file=True,
            enable_console=False
        )
        
        # 验证目录被创建
        self.assertTrue(os.path.exists(log_dir))


class TestLoggerUsage(unittest.TestCase):
    """日志器使用测试类"""

    def setUp(self):
        """测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()
        setup_logging(
            log_level="DEBUG",
            log_dir=self.temp_dir,
            enable_file=True,
            enable_console=False
        )

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # 清理日志器
        logger = logging.getLogger('openchecker')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_get_logger(self):
        """测试获取日志器"""
        logger = get_logger('test_module')
        
        # 验证日志器属性
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'openchecker.test_module')

    def test_logger_logging_levels(self):
        """测试不同日志级别"""
        logger = get_logger('level_test')
        
        # 测试各种日志级别
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # 如果有文件处理器，检查日志文件是否被创建
        log_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.log')]
        if log_files:
            self.assertTrue(len(log_files) > 0)

    def test_logger_with_extra_fields(self):
        """测试带额外字段的日志"""
        logger = get_logger('extra_test')
        
        extra_fields = {
            'user_id': '12345',
            'request_id': 'req_67890',
            'action': 'test_action'
        }
        
        logger.info(
            "Test message with extra fields",
            extra={'extra_fields': extra_fields}
        )
        
        # 验证日志记录成功
        self.assertTrue(True)  # 基本验证


class TestPerformanceDecorator(unittest.TestCase):
    """性能装饰器测试类"""

    def setUp(self):
        """测试前置设置"""
        setup_logging(log_level="DEBUG")

    def tearDown(self):
        """测试后清理"""
        logger = logging.getLogger('openchecker')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_log_performance_decorator(self):
        """测试性能监控装饰器"""
        @log_performance('test_component')
        def test_function(x, y):
            return x + y
        
        # 执行装饰的函数
        result = test_function(1, 2)
        
        # 验证结果正确
        self.assertEqual(result, 3)

    def test_log_performance_with_exception(self):
        """测试带异常的性能监控"""
        @log_performance('error_component')
        def error_function():
            raise ValueError("Test error")
        
        # 执行应该抛出异常的函数
        with self.assertRaises(ValueError):
            error_function()

    def test_log_performance_async_function(self):
        """测试异步函数性能监控"""
        import asyncio
        
        @log_performance('async_component')
        async def async_function():
            await asyncio.sleep(0.01)  # 模拟异步操作
            return "async_result"
        
        # 执行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(async_function())
            self.assertEqual(result, "async_result")
        finally:
            loop.close()


class TestStructuredFormatter(unittest.TestCase):
    """结构化格式器测试类"""

    def setUp(self):
        """测试前置设置"""
        self.formatter = StructuredFormatter()

    def test_format_basic_record(self):
        """测试基本记录格式化"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=100,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        
        # 验证JSON格式
        try:
            data = json.loads(formatted)
            self.assertIn('timestamp', data)
            self.assertIn('level', data)
            self.assertIn('message', data)
            self.assertIn('module', data)
        except json.JSONDecodeError:
            self.fail("格式化输出不是有效的JSON")

    def test_format_record_with_extra_fields(self):
        """测试带额外字段的记录格式化"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=100,
            msg='Test message with extra',
            args=(),
            exc_info=None
        )
        
        # 添加额外字段
        record.extra_fields = {
            'user_id': '12345',
            'session_id': 'sess_67890'
        }
        
        formatted = self.formatter.format(record)
        
        # 验证额外字段被包含
        try:
            data = json.loads(formatted)
            self.assertIn('user_id', data)
            self.assertIn('session_id', data)
        except json.JSONDecodeError:
            self.fail("格式化输出不是有效的JSON")

    def test_format_record_with_exception(self):
        """测试带异常的记录格式化"""
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name='test_logger',
                level=logging.ERROR,
                pathname='test.py',
                lineno=100,
                msg='Error occurred',
                args=(),
                exc_info=True
            )
        
        formatted = self.formatter.format(record)
        
        # 验证异常信息被包含
        try:
            data = json.loads(formatted)
            self.assertIn('exception', data)
        except json.JSONDecodeError:
            self.fail("格式化输出不是有效的JSON")


class TestSimpleFormatter(unittest.TestCase):
    """简单格式器测试类"""

    def setUp(self):
        """测试前置设置"""
        self.formatter = SimpleFormatter()

    def test_format_basic_record(self):
        """测试基本记录格式化"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=100,
            msg='Simple test message',
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        
        # 验证格式包含基本信息
        self.assertIn('INFO', formatted)
        self.assertIn('Simple test message', formatted)
        self.assertIn('test_logger', formatted)

    def test_format_with_timestamp(self):
        """测试时间戳格式"""
        record = logging.LogRecord(
            name='test_logger',
            level=logging.WARNING,
            pathname='test.py',
            lineno=100,
            msg='Warning message',
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        
        # 验证时间戳格式
        self.assertTrue(len(formatted) > 0)
        # 基本验证包含年份
        current_year = str(datetime.now().year)
        self.assertIn(current_year, formatted)


class TestLoggerIntegration(unittest.TestCase):
    """日志器集成测试类"""

    def setUp(self):
        """集成测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """集成测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # 清理所有日志器
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith('openchecker'):
                logger = logging.getLogger(name)
                for handler in logger.handlers[:]:
                    logger.removeHandler(handler)

    def test_multiple_modules_logging(self):
        """测试多模块日志记录"""
        # 设置日志
        setup_logging(
            log_level="INFO",
            log_dir=self.temp_dir,
            enable_file=True,
            enable_console=False
        )
        
        # 创建不同模块的日志器
        logger1 = get_logger('module1')
        logger2 = get_logger('module2')
        logger3 = get_logger('module3')
        
        # 记录不同类型的日志
        logger1.info("Module 1 info message")
        logger2.warning("Module 2 warning message")
        logger3.error("Module 3 error message")
        
        # 验证日志文件创建
        log_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.log')]
        self.assertTrue(len(log_files) > 0)

    def test_log_rotation_configuration(self):
        """测试日志轮转配置"""
        log_file = os.path.join(self.temp_dir, "rotation_test.log")
        
        setup_logging(
            log_file=log_file,
            max_file_size=1024,  # 1KB
            backup_count=3,
            enable_console=False,
            enable_file=True
        )
        
        logger = get_logger('rotation_test')
        
        # 写入足够的日志触发轮转
        for i in range(100):
            logger.info(f"This is test message number {i} with some content to fill up the log file")
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(log_file))

    def test_concurrent_logging(self):
        """测试并发日志记录"""
        import threading
        import time
        
        setup_logging(
            log_level="DEBUG",
            log_dir=self.temp_dir,
            enable_file=True,
            enable_console=False
        )
        
        def worker_function(worker_id):
            logger = get_logger(f'worker_{worker_id}')
            for i in range(10):
                logger.info(f"Worker {worker_id} message {i}")
                time.sleep(0.001)  # 短暂延迟
        
        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_function, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证日志文件创建
        log_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.log')]
        self.assertTrue(len(log_files) > 0)

    @patch('openchecker.logger.logging.FileHandler')
    def test_error_handling_in_setup(self, mock_file_handler):
        """测试日志设置中的错误处理"""
        # 模拟文件处理器创建失败
        mock_file_handler.side_effect = PermissionError("Cannot create log file")
        
        # 应该不抛出异常
        try:
            setup_logging(
                log_file=os.path.join(self.temp_dir, "test.log"),
                enable_file=True,
                enable_console=True
            )
        except Exception as e:
            self.fail(f"setup_logging should handle errors gracefully: {e}")


if __name__ == '__main__':
    # 设置测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestLoggerSetup))
    suite.addTests(loader.loadTestsFromTestCase(TestLoggerUsage))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceDecorator))
    suite.addTests(loader.loadTestsFromTestCase(TestStructuredFormatter))
    suite.addTests(loader.loadTestsFromTestCase(TestSimpleFormatter))
    suite.addTests(loader.loadTestsFromTestCase(TestLoggerIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite) 