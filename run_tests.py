"""
FinNews 测试运行脚本（pytest 封装）

使用方法:
  python run_tests.py                 # 运行所有测试
  python run_tests.py scrapers        # 只运行 scrapers 测试
  python run_tests.py processors      # 只运行 processors 测试
  python run_tests.py storage         # 只运行 storage 测试
  python run_tests.py utils           # 只运行 utils 测试
  python run_tests.py config          # 只运行 config 测试
  python run_tests.py integration     # 只运行集成测试
  python run_tests.py quick           # 快速测试（跳过慢速测试）
  python run_tests.py --quick         # 同上
"""

import sys
import subprocess
from pathlib import Path

# 模块名称到测试路径的映射
MODULE_PATHS = {
    "scrapers": "tests/scrapers",
    "processors": "tests/processors",
    "storage": "tests/storage",
    "utils": "tests/utils",
    "config": "tests/config",
    "integration": "tests/integration tests/test_integration.py",
}


def main():
    args = sys.argv[1:]

    # 构建 pytest 命令
    pytest_args = [sys.executable, "-m", "pytest", "--tb=short"]

    if not args:
        # 运行所有测试
        pytest_args += ["tests/"]
    elif args[0] in ("quick", "--quick"):
        # 快速模式：跳过 slow 和 integration 标记
        pytest_args += ["tests/", "-m", "not slow and not integration"]
    elif args[0] in MODULE_PATHS:
        # 指定模块
        path_spec = MODULE_PATHS[args[0]]
        pytest_args += path_spec.split()
    else:
        print(f"错误: 未知参数 '{args[0]}'")
        print(f"可用模块: {', '.join(list(MODULE_PATHS.keys()) + ['quick'])}")
        sys.exit(1)

    # 传递额外参数
    extra = [a for a in args[1:] if a != "--quick"]
    pytest_args += extra

    result = subprocess.run(pytest_args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
