# OpenChecker 测试文档

## 概述

本文档介绍了 OpenChecker 项目的测试结构、运行方法和最佳实践。我们采用全面的测试策略，确保代码质量和系统可靠性。

## 测试结构

```
test/
├── conftest.py              # pytest配置和夹具
├── pytest.ini              # pytest配置文件
├── requirements.txt         # 测试依赖
├── run_tests.py            # 测试运行脚本
├── README.md               # 测试文档
├── test_agent.py           # Agent模块测试
├── test_message_queue.py   # 消息队列测试
├── test_checkers.py        # 检查器模块测试
├── test_main_api.py        # 主API测试
├── test_logger.py          # 日志模块测试
├── test_platform_adapter.py # 平台适配器测试（已存在）
├── test_token_operator.py  # Token操作测试（已存在）
├── test_user_manager.py    # 用户管理测试（已存在）
└── test_registry.py        # 注册表测试（已存在）
```

## 测试类型

### 1. 单元测试 (Unit Tests)
- **标记**: `@pytest.mark.unit`
- **目的**: 测试单个函数或方法的逻辑
- **特点**: 快速执行，隔离性强，使用模拟对象

### 2. 集成测试 (Integration Tests)
- **标记**: `@pytest.mark.integration`
- **目的**: 测试模块间的交互和数据流
- **特点**: 涉及多个组件，验证接口契约

### 3. 安全测试 (Security Tests)
- **标记**: `@pytest.mark.security`
- **目的**: 验证安全功能和漏洞检测
- **特点**: 重点测试认证、授权、数据保护

### 4. 性能测试 (Performance Tests)
- **标记**: `@pytest.mark.slow`
- **目的**: 评估系统性能和响应时间
- **特点**: 使用基准测试，测量执行时间

## 安装和设置

### 1. 安装测试依赖

```bash
# 方式1：使用测试运行脚本
python test/run_tests.py --install-deps

# 方式2：直接安装
pip install -r test/requirements.txt
```

### 2. 环境配置

确保以下环境变量正确设置：

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/openchecker"
export LOG_LEVEL=DEBUG
export TESTING=true
```

## 运行测试

### 使用测试运行脚本 (推荐)

```bash
# 运行所有测试
python test/run_tests.py --all

# 只运行单元测试
python test/run_tests.py --unit

# 只运行集成测试
python test/run_tests.py --integration

# 运行安全测试
python test/run_tests.py --security

# 并行执行测试
python test/run_tests.py --all --parallel

# 详细输出
python test/run_tests.py --all --verbose

# 代码质量检查
python test/run_tests.py --quality

# 清理测试产物
python test/run_tests.py --clean
```

### 使用 pytest 直接运行

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest test/test_agent.py

# 运行特定测试类
pytest test/test_agent.py::TestAgent

# 运行特定测试方法
pytest test/test_agent.py::TestAgent::test_callback_func_success

# 按标记运行测试
pytest -m unit          # 单元测试
pytest -m integration   # 集成测试
pytest -m security      # 安全测试

# 并行执行
pytest -n auto

# 详细输出
pytest -v -s

# 停在第一个失败
pytest -x

# 重新运行失败的测试
pytest --lf
```

## 测试覆盖率

### 查看覆盖率

测试运行后会生成覆盖率报告：

```bash
# 终端输出覆盖率
pytest --cov=openchecker --cov-report=term-missing

# 生成HTML报告
pytest --cov=openchecker --cov-report=html

# 生成XML报告（用于CI/CD）
pytest --cov=openchecker --cov-report=xml
```

### 覆盖率目标

- **最低覆盖率**: 80%
- **推荐覆盖率**: 90%+
- **核心模块覆盖率**: 95%+

## 测试夹具 (Fixtures)

### 主要夹具

#### 配置相关
- `test_config`: 测试配置数据
- `mock_rabbitmq_config`: 模拟RabbitMQ配置

#### 环境相关
- `temp_directory`: 临时目录
- `test_repo_structure`: 测试仓库结构
- `cleanup_loggers`: 自动清理日志器

#### 应用相关
- `flask_app`: Flask应用测试客户端
- `test_user`: 测试用户对象
- `sample_message`: 示例消息数据

#### 模拟对象
- `mock_platform_adapter`: 模拟平台适配器
- `mock_sonar_response`: 模拟SonarQube响应

### 使用示例

```python
def test_example(temp_directory, test_config):
    """使用夹具的测试示例"""
    # temp_directory 提供临时目录
    # test_config 提供测试配置
    assert os.path.exists(temp_directory)
    assert "OpenCheck" in test_config
```

## 最佳实践

### 1. 测试命名

```python
class TestAgent:
    def test_callback_func_success(self):
        """测试回调函数成功执行"""
        pass
    
    def test_callback_func_invalid_message(self):
        """测试无效消息处理"""
        pass
```

### 2. 使用模拟对象

```python
@patch('openchecker.agent.platform_manager')
def test_with_mock(self, mock_platform):
    """使用模拟对象的测试"""
    mock_platform.download_project_source.return_value = (True, "")
    # 测试逻辑
```

### 3. 测试数据隔离

```python
def setUp(self):
    """每个测试方法前执行"""
    self.temp_dir = tempfile.mkdtemp()

def tearDown(self):
    """每个测试方法后执行"""
    if os.path.exists(self.temp_dir):
        shutil.rmtree(self.temp_dir)
```

### 4. 异常测试

```python
def test_error_handling(self):
    """测试错误处理"""
    with self.assertRaises(ValueError):
        problematic_function()
```

### 5. 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    ("read", "PERMISSION_LEVEL_READ"),
    ("write", "PERMISSION_LEVEL_WRITE"),
    ("none", "PERMISSION_LEVEL_NONE"),
])
def test_permission_levels(self, input, expected):
    """参数化测试权限级别"""
    result = get_permission_level(input)
    assert result == expected
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r test/requirements.txt
      
      - name: Run tests
        run: python test/run_tests.py --all
      
      - name: Upload coverage
        uses: codecov/codecov-action@v1
        with:
          file: ./coverage.xml
```

## 调试测试

### 1. 使用详细输出

```bash
pytest -v -s test/test_agent.py::TestAgent::test_callback_func_success
```

### 2. 使用 pdb 调试器

```python
def test_debug_example(self):
    """调试测试示例"""
    import pdb; pdb.set_trace()
    # 测试逻辑
```

### 3. 查看日志输出

```python
def test_with_logs(self, capture_logs):
    """捕获日志的测试"""
    logger = get_logger('test')
    logger.info("测试日志")
    
    logs = capture_logs.getvalue()
    assert "测试日志" in logs
```

## 性能监控

### 基准测试

```python
@pytest.mark.benchmark
def test_performance(benchmark):
    """性能基准测试"""
    result = benchmark(expensive_function, arg1, arg2)
    assert result is not None
```

### 监控指标

- 测试执行时间
- 内存使用情况
- API响应时间
- 数据库查询性能

## 故障排除

### 常见问题

1. **模块导入错误**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **权限问题**
   ```bash
   chmod +x test/run_tests.py
   ```

3. **依赖冲突**
   ```bash
   pip install --upgrade -r test/requirements.txt
   ```

4. **临时文件清理**
   ```bash
   python test/run_tests.py --clean
   ```

## 贡献指南

### 添加新测试

1. 确定测试类型和位置
2. 编写测试用例
3. 添加适当的标记
4. 更新文档

### 测试审查清单

- [ ] 测试命名清晰
- [ ] 使用适当的夹具
- [ ] 包含正面和负面测试
- [ ] 错误处理完整
- [ ] 文档和注释充分
- [ ] 覆盖率达到要求

## 联系信息

如有测试相关问题，请联系：
- 项目维护者：[Guoqiang QI](guoqiang.qi1@gmail.com)
- 提交Issue：[GitHub Issues](https://github.com/Laniakea2012/openchecker/issues) 