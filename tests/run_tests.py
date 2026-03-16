<<<<<<< HEAD
"""运行所有单元测试."""

import unittest
import sys
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def run_all_tests():
    """运行所有单元测试。"""
    # 发现测试
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent

    # 加载所有 test_*.py 文件
    suite = loader.discover(
        start_dir=str(start_dir),
        pattern="test_*.py"
    )

    # 运行测试
    runner = unittest.TextTestRunner(
        verbosity=2,
        descriptions=True
    )
    result = runner.run(suite)

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"总测试数：{result.testsRun}")
    print(f"成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败：{len(result.failures)}")
    print(f"错误：{len(result.errors)}")

    if result.failures:
        print("\n失败测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\n错误测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
=======
"""运行所有单元测试."""

import unittest
import sys
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def run_all_tests():
    """运行所有单元测试。"""
    # 发现测试
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent

    # 加载所有 test_*.py 文件
    suite = loader.discover(
        start_dir=str(start_dir),
        pattern="test_*.py"
    )

    # 运行测试
    runner = unittest.TextTestRunner(
        verbosity=2,
        descriptions=True
    )
    result = runner.run(suite)

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"总测试数：{result.testsRun}")
    print(f"成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败：{len(result.failures)}")
    print(f"错误：{len(result.errors)}")

    if result.failures:
        print("\n失败测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\n错误测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
