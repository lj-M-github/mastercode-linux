"""运行所有单元测试 - 使用 pytest."""

import subprocess
import sys


def run_all_tests(verbosity: int = 2):
    """运行所有单元测试。

    Args:
        verbosity: 详细程度 (1=简要，2=详细)

    Returns:
        bool: 测试是否全部通过
    """
    # 使用 pytest 运行测试
    cmd = [sys.executable, "-m", "pytest", "tests/", f"-{'v' * verbosity}"]

    print("=" * 60)
    print("运行测试套件...")
    print("=" * 60)

    result = subprocess.run(cmd)

    # 打印总结
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)

    return result.returncode == 0


if __name__ == "__main__":
    verbosity = 2 if "-v" in sys.argv else 1
    success = run_all_tests(verbosity)
    sys.exit(0 if success else 1)
