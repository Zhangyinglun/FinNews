"""
FinNews 测试运行脚本 | FinNews Test Runner
统一的测试执行脚本，支持运行所有测试或指定模块的测试

使用方法 | Usage:
  python run_tests.py                 # 运行所有测试
  python run_tests.py scrapers        # 只运行scrapers测试
  python run_tests.py processors      # 只运行processors测试
  python run_tests.py storage         # 只运行storage测试
  python run_tests.py utils           # 只运行utils测试
  python run_tests.py config          # 只运行config测试
  python run_tests.py integration     # 只运行集成测试
  python run_tests.py quick           # 快速测试（跳过慢速测试）
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent))

# 测试模块定义
TEST_MODULES = {
    "scrapers": [
        "tests/scrapers/test_tavily.py",
        "tests/scrapers/test_yfinance.py",
        "tests/scrapers/test_rss.py",
        "tests/scrapers/test_fred.py",
        "tests/scrapers/test_alpha_vantage.py",
        "tests/scrapers/test_content_fetcher.py",
    ],
    "processors": [
        "tests/processors/test_cleaner.py",
        "tests/processors/test_deduplicator.py",
    ],
    "storage": [
        "tests/storage/test_json_storage.py",
    ],
    "utils": [
        "tests/utils/test_gmail_smtp.py",
        "tests/utils/test_openrouter_digest.py",
        "tests/utils/test_digest_to_file.py",
    ],
    "config": [
        "tests/config/test_config.py",
    ],
    "integration": [
        "tests/test_integration.py",
    ],
}

# 快速测试（跳过耗时的测试）
QUICK_TESTS = {
    "scrapers": [
        "tests/scrapers/test_yfinance.py",
        "tests/scrapers/test_fred.py",
    ],
    "processors": [
        "tests/processors/test_cleaner.py",
        "tests/processors/test_deduplicator.py",
    ],
    "config": [
        "tests/config/test_config.py",
    ],
}


def print_header(text: str):
    """打印标题"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_section(text: str):
    """打印分节标题"""
    print("\n" + "-" * 80)
    print(f"  {text}")
    print("-" * 80)


def run_test_file(test_file: str) -> bool:
    """运行单个测试文件

    Args:
        test_file: 测试文件路径

    Returns:
        测试是否成功
    """
    test_path = Path(test_file)

    if not test_path.exists():
        print(f"⚠️ 测试文件不存在: {test_file}")
        return False

    print(f"\n▶️ 运行: {test_file}")
    print("-" * 40)

    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=False,
            text=True,
            timeout=300,  # 5分钟超时
        )

        if result.returncode == 0:
            print(f"✅ 通过: {test_file}")
            return True
        else:
            print(f"❌ 失败: {test_file} (退出码: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏱️ 超时: {test_file}")
        return False
    except Exception as e:
        print(f"❌ 错误: {test_file} - {e}")
        return False


def run_tests(module: str = None, quick: bool = False):
    """运行测试

    Args:
        module: 要运行的模块名称，None表示运行所有测试
        quick: 是否只运行快速测试
    """
    start_time = datetime.now()

    print_header(f"FinNews 测试套件 | FinNews Test Suite")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if quick:
        print("模式: 快速测试 (Quick Tests)")
        tests_to_run = QUICK_TESTS
    else:
        tests_to_run = TEST_MODULES

    if module:
        if module not in tests_to_run:
            print(f"\n❌ 错误: 未知的模块 '{module}'")
            print(f"可用模块: {', '.join(tests_to_run.keys())}")
            return

        print(f"范围: {module} 模块")
        modules_to_test = {module: tests_to_run[module]}
    else:
        print("范围: 所有测试")
        modules_to_test = tests_to_run

    # 运行测试
    results = {}
    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    for module_name, test_files in modules_to_test.items():
        print_section(f"测试模块: {module_name}")

        module_results = []
        for test_file in test_files:
            total_tests += 1
            success = run_test_file(test_file)
            module_results.append((test_file, success))

            if success:
                passed_tests += 1
            else:
                failed_tests += 1

        results[module_name] = module_results

    # 打印总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print_header("测试总结 | Test Summary")

    print(f"\n总计: {total_tests} 个测试")
    print(f"✅ 通过: {passed_tests} 个")
    print(f"❌ 失败: {failed_tests} 个")
    print(f"⏱️ 用时: {duration:.2f} 秒")

    # 详细结果
    print("\n详细结果:")
    for module_name, module_results in results.items():
        passed = sum(1 for _, success in module_results if success)
        total = len(module_results)
        status = "✅" if passed == total else "❌"
        print(f"\n{status} {module_name}: {passed}/{total}")

        for test_file, success in module_results:
            status_icon = "✅" if success else "❌"
            test_name = Path(test_file).stem
            print(f"    {status_icon} {test_name}")

    # 如果有失败的测试，显示失败列表
    if failed_tests > 0:
        print("\n失败的测试:")
        for module_name, module_results in results.items():
            for test_file, success in module_results:
                if not success:
                    print(f"  ❌ {test_file}")

    # 返回码
    print("\n" + "=" * 80)
    if failed_tests == 0:
        print("🎉 所有测试通过！")
        sys.exit(0)
    else:
        print(f"⚠️ 有 {failed_tests} 个测试失败")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FinNews 测试运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_tests.py                 # 运行所有测试
  python run_tests.py scrapers        # 只运行scrapers测试
  python run_tests.py --quick         # 运行快速测试
  python run_tests.py integration     # 只运行集成测试
        """,
    )

    parser.add_argument(
        "module",
        nargs="?",
        choices=list(TEST_MODULES.keys()) + ["quick"],
        help="要运行的测试模块（留空运行所有测试）",
    )

    parser.add_argument("--quick", action="store_true", help="只运行快速测试")

    args = parser.parse_args()

    if args.module == "quick":
        run_tests(module=None, quick=True)
    else:
        run_tests(module=args.module, quick=args.quick)


if __name__ == "__main__":
    main()
