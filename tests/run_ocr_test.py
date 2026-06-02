"""
OCR 测试运行脚本

用于快速运行 OCR 集成测试
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from tests.test_config import TEST_CONFIGS


def run_test(config_name: str = "TCP7", verbose: bool = True):
    """
    运行 OCR 测试
    
    Args:
        config_name: 测试配置名称，如 "TCP7", "TCP3"
        verbose: 是否显示详细输出
    """
    if config_name not in TEST_CONFIGS:
        print(f"[ERROR] 未找到配置 '{config_name}'")
        print(f"可用的配置: {', '.join(TEST_CONFIGS.keys())}")
        return

    config = TEST_CONFIGS[config_name]
    print(f"\n{'='*60}")
    print(f"准备运行 OCR 测试")
    print(f"{'='*60}")
    print(f"测试配置: {config['name']}")
    print(f"描述: {config['description']}")
    print(f"IP: {config['ip']}")
    print(f"车位号: {config['park_no']}")
    print(f"{'='*60}\n")

    # 构建 pytest 参数
    pytest_args = [
        "tests/integration/test_ocr_integration.py",
        f"-k", f"test_ocr_barcode_{config_name.lower()}",
    ]
    
    if verbose:
        pytest_args.extend(["-v", "-s"])

    # 运行测试
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print(f"\n{'='*60}")
        print(f"[OK] 测试成功完成!")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"[FAILED] 测试失败，退出码: {exit_code}")
        print(f"{'='*60}\n")
    
    return exit_code


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行 OCR 集成测试")
    parser.add_argument(
        "--config",
        type=str,
        default="TCP7",
        choices=list(TEST_CONFIGS.keys()),
        help="测试配置名称 (默认: TCP7)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="减少输出信息"
    )
    
    args = parser.parse_args()
    
    exit_code = run_test(
        config_name=args.config,
        verbose=not args.quiet
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
