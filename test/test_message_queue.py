#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChecker Message Queue Tests

This module provides comprehensive tests for the message queue functionality
including connection management, publishing, consuming, and error handling.

Author: OpenChecker Team
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time
import pika
import json

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from openchecker.message_queue import (
    test_rabbitmq_connection,
    create_queue,
    publish_message,
    consumer,
    check_queue_status,
    heartbeat_sender
)


class TestMessageQueue(unittest.TestCase):
    """消息队列测试类"""

    def setUp(self):
        """测试前置设置"""
        self.test_config = {
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'virtual_host': '/'
        }
        self.queue_name = "test_queue"
        self.test_message = {"test": "message", "timestamp": "2024-01-01T00:00:00Z"}

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_rabbitmq_connection_success(self, mock_connection):
        """测试RabbitMQ连接成功"""
        # 设置模拟
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # 执行测试
        result = test_rabbitmq_connection(self.test_config)
        
        # 验证结果
        self.assertTrue(result)
        mock_connection.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_rabbitmq_connection_failure(self, mock_connection):
        """测试RabbitMQ连接失败"""
        # 设置连接异常
        mock_connection.side_effect = pika.exceptions.AMQPConnectionError("Connection failed")
        
        # 执行测试
        result = test_rabbitmq_connection(self.test_config)
        
        # 验证结果
        self.assertFalse(result)

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_create_queue_success(self, mock_connection):
        """测试队列创建成功"""
        # 设置模拟
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # 执行测试
        queue_args = {"x-message-ttl": 60000}
        result = create_queue(self.test_config, self.queue_name, queue_args)
        
        # 验证结果
        self.assertTrue(result)
        mock_channel.queue_declare.assert_called_once_with(
            queue=self.queue_name, 
            durable=True, 
            arguments=queue_args
        )

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_create_queue_failure(self, mock_connection):
        """测试队列创建失败"""
        # 设置模拟异常
        mock_conn = Mock()
        mock_channel = Mock()
        mock_channel.queue_declare.side_effect = pika.exceptions.AMQPChannelError("Queue creation failed")
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # 执行测试
        result = create_queue(self.test_config, self.queue_name)
        
        # 验证结果
        self.assertFalse(result)

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_publish_message_success(self, mock_connection):
        """测试消息发布成功"""
        # 设置模拟
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # 执行测试
        result = publish_message(self.test_config, self.queue_name, self.test_message)
        
        # 验证结果
        self.assertTrue(result)
        mock_channel.basic_publish.assert_called_once()
        
        # 验证发布的消息内容
        call_args = mock_channel.basic_publish.call_args
        self.assertEqual(call_args[1]['routing_key'], self.queue_name)
        self.assertIn('test', call_args[1]['body'])

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_publish_message_failure(self, mock_connection):
        """测试消息发布失败"""
        # 设置模拟异常
        mock_conn = Mock()
        mock_channel = Mock()
        mock_channel.basic_publish.side_effect = pika.exceptions.AMQPChannelError("Publish failed")
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # 执行测试
        result = publish_message(self.test_config, self.queue_name, self.test_message)
        
        # 验证结果
        self.assertFalse(result)

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_check_queue_status_success(self, mock_connection):
        """测试队列状态检查成功"""
        # 设置模拟
        mock_conn = Mock()
        mock_channel = Mock()
        mock_method = Mock()
        mock_method.message_count = 5
        mock_method.consumer_count = 2
        mock_channel.queue_declare.return_value = mock_method
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # 执行测试
        result = check_queue_status(self.test_config, self.queue_name)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['message_count'], 5)
        self.assertEqual(result['consumer_count'], 2)

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_check_queue_status_failure(self, mock_connection):
        """测试队列状态检查失败"""
        # 设置模拟异常
        mock_connection.side_effect = pika.exceptions.AMQPConnectionError("Connection failed")
        
        # 执行测试
        result = check_queue_status(self.test_config, self.queue_name)
        
        # 验证结果
        self.assertIsNone(result)

    def test_heartbeat_sender(self):
        """测试心跳发送器"""
        # 创建模拟连接
        mock_connection = Mock()
        mock_connection.is_open = True
        
        # 创建线程来测试心跳
        heartbeat_thread = threading.Thread(
            target=heartbeat_sender,
            args=(mock_connection,),
            daemon=True
        )
        
        # 启动并等待短时间
        heartbeat_thread.start()
        time.sleep(0.1)  # 等待短时间
        
        # 验证心跳调用
        self.assertTrue(heartbeat_thread.is_alive())


class TestConsumer(unittest.TestCase):
    """消费者测试类"""

    def setUp(self):
        """测试前置设置"""
        self.test_config = {
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest'
        }
        self.queue_name = "test_consumer_queue"
        self.callback_called = False
        self.received_message = None

    def mock_callback(self, ch, method, properties, body):
        """模拟回调函数"""
        self.callback_called = True
        self.received_message = body
        ch.basic_ack(delivery_tag=method.delivery_tag)

    @patch('openchecker.message_queue.pika.BlockingConnection')
    @patch('openchecker.message_queue.heartbeat_sender')
    def test_consumer_connection_retry(self, mock_heartbeat, mock_connection):
        """测试消费者连接重试机制"""
        # 设置第一次连接失败，第二次成功
        mock_connection.side_effect = [
            pika.exceptions.ConnectionClosedByBroker("First attempt fails"),
            Mock()  # 第二次成功
        ]
        
        # 使用线程运行消费者以避免阻塞
        consumer_thread = threading.Thread(
            target=consumer,
            args=(self.test_config, self.queue_name, self.mock_callback),
            daemon=True
        )
        
        consumer_thread.start()
        time.sleep(0.1)  # 给足时间进行重试
        
        # 验证连接被调用多次（重试机制）
        self.assertGreater(mock_connection.call_count, 1)

    @patch('openchecker.message_queue.logger')
    def test_consumer_error_logging(self, mock_logger):
        """测试消费者错误日志记录"""
        with patch('openchecker.message_queue.pika.BlockingConnection') as mock_connection:
            mock_connection.side_effect = Exception("Critical error")
            
            # 执行消费者
            result = consumer(self.test_config, self.queue_name, self.mock_callback)
            
            # 验证错误日志
            mock_logger.error.assert_called()
            self.assertIsNotNone(result)


class TestMessageQueueIntegration(unittest.TestCase):
    """消息队列集成测试类"""

    def setUp(self):
        """集成测试前置设置"""
        self.test_config = {
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest'
        }
        self.integration_queue = "integration_test_queue"

    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_publish_consume_workflow(self, mock_connection):
        """测试发布-消费工作流"""
        # 设置模拟连接和通道
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # 模拟消息
        test_message = {"test": "integration", "id": 12345}
        
        # 测试发布
        publish_result = publish_message(self.test_config, self.integration_queue, test_message)
        self.assertTrue(publish_result)
        
        # 验证发布调用
        mock_channel.basic_publish.assert_called_once()
        
        # 测试队列创建
        create_result = create_queue(self.test_config, self.integration_queue)
        self.assertTrue(create_result)
        
        # 验证队列创建调用
        mock_channel.queue_declare.assert_called_once()

    def test_message_serialization(self):
        """测试消息序列化和反序列化"""
        original_message = {
            "command_list": ["test-command"],
            "project_url": "https://github.com/test/repo",
            "metadata": {"version": "1.0.0"},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # 序列化
        serialized = json.dumps(original_message)
        
        # 反序列化
        deserialized = json.loads(serialized)
        
        # 验证数据完整性
        self.assertEqual(original_message, deserialized)
        self.assertEqual(original_message["command_list"], deserialized["command_list"])
        self.assertEqual(original_message["project_url"], deserialized["project_url"])

    @patch('openchecker.message_queue.time.sleep')
    @patch('openchecker.message_queue.pika.BlockingConnection')
    def test_connection_resilience(self, mock_connection, mock_sleep):
        """测试连接弹性和重连机制"""
        # 模拟连接失败然后成功
        connection_attempts = [
            pika.exceptions.AMQPConnectionError("Network error"),
            pika.exceptions.ConnectionClosedByBroker("Broker restart"),
            Mock()  # 最终成功
        ]
        mock_connection.side_effect = connection_attempts
        
        # 执行测试
        def dummy_callback(ch, method, properties, body):
            pass
        
        consumer_thread = threading.Thread(
            target=consumer,
            args=(self.test_config, "resilience_queue", dummy_callback),
            daemon=True
        )
        consumer_thread.start()
        time.sleep(0.1)
        
        # 验证重连尝试
        self.assertGreaterEqual(mock_connection.call_count, 2)
        mock_sleep.assert_called()


if __name__ == '__main__':
    # 设置测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMessageQueue))
    suite.addTests(loader.loadTestsFromTestCase(TestConsumer))
    suite.addTests(loader.loadTestsFromTestCase(TestMessageQueueIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite) 