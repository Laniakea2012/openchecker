#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChecker Test Runner

This script provides convenient test execution with various options
for running different types of tests and generating reports.

Author: OpenChecker Team
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path


def run_command(cmd, description=""):
    """执行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description or cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print("输出:")
        print(result.stdout)
    
    if result.stderr:
        print("错误:")
        print(result.stderr)
    
    return result.returncode == 0, result


def install_dependencies():
    """安装测试依赖"""
    print("安装测试依赖...")
    cmd = "pip install -r test/requirements.txt"
    success, result = run_command(cmd, "安装测试依赖")
    return success


def run_unit_tests(verbose=False, coverage=True):
    """运行单元测试"""
    cmd_parts = ["python", "-m", "pytest", "-m", "unit"]
    
    if verbose:
        cmd_parts.extend(["-v", "-s"])
    
    if coverage:
        cmd_parts.extend([
            "--cov=openchecker",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/unit"
        ])
    
    cmd = " ".join(cmd_parts)
    return run_command(cmd, "运行单元测试")


def run_integration_tests(verbose=False):
    """运行集成测试"""
    cmd_parts = ["python", "-m", "pytest", "-m", "integration"]
    
    if verbose:
        cmd_parts.extend(["-v", "-s"])
    
    cmd = " ".join(cmd_parts)
    return run_command(cmd, "运行集成测试")


def run_all_tests(verbose=False, parallel=False):
    """运行所有测试"""
    cmd_parts = ["python", "-m", "pytest"]
    
    if verbose:
        cmd_parts.extend(["-v", "-s"])
    
    if parallel:
        cmd_parts.extend(["-n", "auto"])
    
    cmd_parts.extend([
        "--cov=openchecker",
        "--cov-report=term-missing", 
        "--cov-report=html:htmlcov/all",
        "--cov-report=xml",
        "--junit-xml=test-results.xml"
    ])
    
    cmd = " ".join(cmd_parts)
    return run_command(cmd, "运行所有测试")


def run_security_tests():
    """运行安全相关测试"""
    cmd = "python -m pytest -m security -v"
    return run_command(cmd, "运行安全测试")


def run_performance_tests():
    """运行性能测试"""
    cmd = "python -m pytest -m slow --benchmark-only"
    return run_command(cmd, "运行性能测试")


def run_code_quality_checks():
    """运行代码质量检查"""
    checks = [
        ("flake8 openchecker/", "运行Flake8代码风格检查"),
        ("black --check openchecker/", "运行Black代码格式检查"),
        ("isort --check-only openchecker/", "运行isort导入排序检查"),
        ("mypy openchecker/", "运行MyPy类型检查")
    ]
    
    results = []
    for cmd, desc in checks:
        success, result = run_command(cmd, desc)
        results.append((desc, success))
    
    return results


def generate_test_report():
    """生成测试报告"""
    print("\n" + "="*60)
    print("生成测试报告")
    print("="*60)
    
    # 检查覆盖率报告
    if os.path.exists("htmlcov/all/index.html"):
        print("✓ HTML覆盖率报告: htmlcov/all/index.html")
    
    if os.path.exists("coverage.xml"):
        print("✓ XML覆盖率报告: coverage.xml")
    
    if os.path.exists("test-results.xml"):
        print("✓ JUnit测试结果: test-results.xml")
    
    # 生成简单的测试摘要
    try:
        with open("test-summary.json", "w") as f:
            summary = {
                "timestamp": "2024-01-01T00:00:00Z",
                "test_run": "completed",
                "reports": {
                    "coverage_html": "htmlcov/all/index.html",
                    "coverage_xml": "coverage.xml", 
                    "junit_xml": "test-results.xml"
                }
            }
            json.dump(summary, f, indent=2)
        print("✓ 测试摘要: test-summary.json")
    except Exception as e:
        print(f"× 生成测试摘要失败: {e}")


def clean_test_artifacts():
    """清理测试产物"""
    artifacts = [
        "htmlcov/",
        "coverage.xml",
        "test-results.xml", 
        "test-summary.json",
        "tests.log",
        ".coverage",
        ".pytest_cache/",
        "__pycache__/"
    ]
    
    print("\n清理测试产物...")
    for artifact in artifacts:
        path = Path(artifact)
        if path.exists():
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
                print(f"✓ 删除目录: {artifact}")
            else:
                path.unlink()
                print(f"✓ 删除文件: {artifact}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenChecker测试运行器")
    
    parser.add_argument("--install-deps", action="store_true",
                       help="安装测试依赖")
    parser.add_argument("--unit", action="store_true",
                       help="只运行单元测试")
    parser.add_argument("--integration", action="store_true", 
                       help="只运行集成测试")
    parser.add_argument("--security", action="store_true",
                       help="只运行安全测试")
    parser.add_argument("--performance", action="store_true",
                       help="只运行性能测试") 
    parser.add_argument("--quality", action="store_true",
                       help="运行代码质量检查")
    parser.add_argument("--all", action="store_true",
                       help="运行所有测试")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="详细输出")
    parser.add_argument("--parallel", "-p", action="store_true",
                       help="并行执行测试")
    parser.add_argument("--no-coverage", action="store_true",
                       help="禁用覆盖率测试")
    parser.add_argument("--clean", action="store_true",
                       help="清理测试产物")
    parser.add_argument("--report", action="store_true",
                       help="生成测试报告")
    
    args = parser.parse_args()
    
    # 清理产物
    if args.clean:
        clean_test_artifacts()
        return
    
    # 安装依赖
    if args.install_deps:
        if not install_dependencies():
            print("依赖安装失败")
            sys.exit(1)
    
    # 代码质量检查
    if args.quality:
        results = run_code_quality_checks()
        failed_checks = [desc for desc, success in results if not success]
        if failed_checks:
            print(f"\n代码质量检查失败: {', '.join(failed_checks)}")
            sys.exit(1)
        return
    
    # 运行测试
    success = True
    
    if args.unit:
        success, _ = run_unit_tests(args.verbose, not args.no_coverage)
    elif args.integration:
        success, _ = run_integration_tests(args.verbose)
    elif args.security:
        success, _ = run_security_tests()
    elif args.performance:
        success, _ = run_performance_tests()
    elif args.all:
        success, _ = run_all_tests(args.verbose, args.parallel)
    else:
        # 默认运行所有测试
        success, _ = run_all_tests(args.verbose, args.parallel)
    
    # 生成报告
    if args.report or args.all:
        generate_test_report()
    
    # 退出状态
    if not success:
        print("\n测试执行失败")
        sys.exit(1)
    else:
        print("\n测试执行成功")


if __name__ == "__main__":
    main() 