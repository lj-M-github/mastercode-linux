<<<<<<< HEAD
#!/usr/bin/env python3
"""阶段 2：语义翻译引擎测试脚本。

本脚本用于测试 LLM 驱动的代码生成功能：
1. 测试 System Prompt 效果
2. 测试 YAML 生成和验证
3. 测试端到端流程（RAG 查询 → 代码生成）

使用方法:
    python tests/test_stage2.py

依赖:
    - OPENAI_API_KEY 环境变量（可选，无 key 时使用模拟模式）
"""

import os
import sys
import io
from pathlib import Path

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.generator import (
    CodeGenerator,
    generate_ansible_code,
    validate_yaml,
    YAMLValidationError
)
from agent.rag_querier import RAGQuerier


# 状态符号（ASCII 兼容）
SUCCESS_MARK = "[OK]"
FAIL_MARK = "[FAIL]"


def print_separator(title: str = ""):
    """打印分隔线。"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def test_mock_generation():
    """测试模拟模式下的代码生成。"""
    print_separator("测试 1: 模拟模式代码生成")

    generator = CodeGenerator()

    # 测试用例
    test_cases = [
        {
            "rule_id": "1.1",
            "section_title": "Ensure SSH root login is disabled",
            "cloud_provider": "alibaba",
            "remediation": "1. Edit /etc/ssh/sshd_config\n2. Set PermitRootLogin to no\n3. Restart sshd service"
        },
        {
            "rule_id": "2.3",
            "section_title": "Ensure file permissions are set",
            "cloud_provider": "tencent",
            "remediation": "Set /etc/shadow permissions to 0000"
        },
        {
            "rule_id": "1.5",
            "section_title": "Ensure password complexity is configured",
            "cloud_provider": "google",
            "remediation": "Configure pam_pwquality module with minlen=14, dcredit=-1, ucredit=-1, ocredit=-1, lcredit=-1"
        }
    ]

    for case in test_cases:
        print(f"\n规则：{case['rule_id']} - {case['section_title']}")
        print(f"云厂商：{case['cloud_provider']}")
        print("-" * 50)

        result = generator.generate(**case)

        if result.success:
            print(f"{SUCCESS_MARK} 生成成功，共 {len(result.tasks)} 个任务")
            for task in result.tasks:
                print(f"  - {task.name} (模块：{task.module})")
        else:
            print(f"{FAIL_MARK} 生成失败：{result.error}")

    return True


def test_yaml_validation():
    """测试 YAML 验证功能。"""
    print_separator("测试 2: YAML 语法验证")

    # 合法的 YAML
    valid_yaml = """
- name: Test task
  lineinfile:
    path: /etc/test
    line: "test=value"
"""

    # 非法的 YAML
    invalid_yaml = """
- name: Test task
  lineinfile:
    path: /etc/test
    line: "test=value"
  invalid_indent:
 - wrong
"""

    is_valid, error = validate_yaml(valid_yaml)
    print(f"合法 YAML 验证：{SUCCESS_MARK if is_valid else FAIL_MARK} 通过")

    is_valid, error = validate_yaml(invalid_yaml)
    print(f"非法 YAML 验证：{SUCCESS_MARK if not is_valid else FAIL_MARK} 正确识别")
    if error:
        print(f"  错误信息：{error[:100]}...")

    return True


def test_with_rag_results():
    """测试与 RAG 查询结果结合使用。"""
    print_separator("测试 3: RAG 查询 + 代码生成")

    try:
        # 尝试查询向量数据库
        querier = RAGQuerier()
        results = querier.query("SSH", n_results=2)

        if not results:
            print("向量数据库中无 SSH 相关数据，使用模拟数据测试")
            # 使用模拟数据
            from agent.rag_querier import QueryResult
            results = [
                QueryResult(
                    content="SSH configuration",
                    rule_id="1.1",
                    section_title="Ensure SSH root login is disabled",
                    cloud_provider="alibaba",
                    remediation="Disable root login in sshd_config",
                    page_number=10,
                    source_file="test.pdf",
                    distance=0.1
                )
            ]

        generator = CodeGenerator()

        for result in results:
            print(f"\n查询结果：{result.rule_id} - {result.section_title}")
            print(f"距离：{result.distance:.4f}")
            print("-" * 50)

            gen_result = generator.generate(
                rule_id=result.rule_id,
                section_title=result.section_title,
                cloud_provider=result.cloud_provider,
                remediation=result.remediation
            )

            if gen_result.success:
                print(f"✓ 代码生成成功")
                print("\n生成的 Ansible 代码:")
                print("-" * 50)
                # 重新生成 YAML 用于显示
                for task in gen_result.tasks:
                    print(f"- name: {task.name}")
                    print(f"  {task.module}:")
                    for k, v in task.params.items():
                        print(f"    {k}: {v}")
                    print()
            else:
                print(f"✗ 代码生成失败：{gen_result.error}")

        return True

    except Exception as e:
        print(f"测试跳过：{e}")
        return False


def test_batch_generation():
    """测试批量代码生成。"""
    print_separator("测试 4: 批量代码生成")

    test_rules = [
        ("1.1", "SSH 配置", "禁用 root 登录", "alibaba"),
        ("1.2", "SSH 配置", "设置 Protocol 2", "alibaba"),
        ("2.1", "日志审计", "启用 rsyslog", "tencent"),
        ("2.2", "日志审计", "配置 logrotate", "tencent"),
        ("3.1", "网络配置", "启用防火墙", "google"),
    ]

    generator = CodeGenerator()
    success_count = 0

    for rule_id, title, remediation, provider in test_rules:
        result = generator.generate(
            rule_id=rule_id,
            section_title=title,
            cloud_provider=provider,
            remediation=remediation
        )

        if result.success:
            success_count += 1
            status = SUCCESS_MARK
        else:
            status = FAIL_MARK

        print(f"{status} {rule_id}: {title} -> {len(result.tasks)} 个任务")

    print(f"\n总计：{success_count}/{len(test_rules)} 成功")
    return success_count == len(test_rules)


def test_convenience_function():
    """测试便捷函数。"""
    print_separator("测试 5: 便捷函数测试")

    result = generate_ansible_code(
        rule_id="1.1",
        section_title="测试规则",
        remediation="配置 SSH 安全设置",
        cloud_provider="alibaba"
    )

    print(f"规则：{result.rule_id}")
    print(f"成功：{result.success}")
    print(f"任务数：{len(result.tasks)}")
    print(f"模型：{result.model or '模拟模式'}")

    if result.success:
        for task in result.tasks:
            print(f"  - {task.name} ({task.module})")

    return result.success


def main():
    """运行所有测试。"""
    print_separator("阶段 2：语义翻译引擎测试")
    print(f"API Key 状态：{'已配置' if os.getenv('OPENAI_API_KEY') else '未配置 (使用模拟模式)'}")

    results = []

    # 运行测试
    results.append(("模拟模式生成", test_mock_generation()))
    results.append(("YAML 验证", test_yaml_validation()))
    results.append(("RAG 集成", test_with_rag_results()))
    results.append(("批量生成", test_batch_generation()))
    results.append(("便捷函数", test_convenience_function()))

    # 总结
    print_separator("测试总结")
    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = SUCCESS_MARK if result else FAIL_MARK
        print(f"  {status}: {name}")

    print(f"\n总计：{passed}/{total} 测试通过")

    if passed == total:
        print("\n[SUCCESS] 阶段 2 测试全部通过!")
        return 0
    else:
        print("\n[WARNING] 部分测试未通过，请检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())
=======
#!/usr/bin/env python3
"""阶段 2：语义翻译引擎测试脚本。

本脚本用于测试 LLM 驱动的代码生成功能：
1. 测试 System Prompt 效果
2. 测试 YAML 生成和验证
3. 测试端到端流程（RAG 查询 → 代码生成）

使用方法:
    python tests/test_stage2.py

依赖:
    - OPENAI_API_KEY 环境变量（可选，无 key 时使用模拟模式）
"""

import os
import sys
import io
from pathlib import Path

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.generator import (
    CodeGenerator,
    generate_ansible_code,
    validate_yaml,
    YAMLValidationError
)
from agent.rag_querier import RAGQuerier


# 状态符号（ASCII 兼容）
SUCCESS_MARK = "[OK]"
FAIL_MARK = "[FAIL]"


def print_separator(title: str = ""):
    """打印分隔线。"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def test_mock_generation():
    """测试模拟模式下的代码生成。"""
    print_separator("测试 1: 模拟模式代码生成")

    generator = CodeGenerator()

    # 测试用例
    test_cases = [
        {
            "rule_id": "1.1",
            "section_title": "Ensure SSH root login is disabled",
            "cloud_provider": "alibaba",
            "remediation": "1. Edit /etc/ssh/sshd_config\n2. Set PermitRootLogin to no\n3. Restart sshd service"
        },
        {
            "rule_id": "2.3",
            "section_title": "Ensure file permissions are set",
            "cloud_provider": "tencent",
            "remediation": "Set /etc/shadow permissions to 0000"
        },
        {
            "rule_id": "1.5",
            "section_title": "Ensure password complexity is configured",
            "cloud_provider": "google",
            "remediation": "Configure pam_pwquality module with minlen=14, dcredit=-1, ucredit=-1, ocredit=-1, lcredit=-1"
        }
    ]

    for case in test_cases:
        print(f"\n规则：{case['rule_id']} - {case['section_title']}")
        print(f"云厂商：{case['cloud_provider']}")
        print("-" * 50)

        result = generator.generate(**case)

        if result.success:
            print(f"{SUCCESS_MARK} 生成成功，共 {len(result.tasks)} 个任务")
            for task in result.tasks:
                print(f"  - {task.name} (模块：{task.module})")
        else:
            print(f"{FAIL_MARK} 生成失败：{result.error}")

    return True


def test_yaml_validation():
    """测试 YAML 验证功能。"""
    print_separator("测试 2: YAML 语法验证")

    # 合法的 YAML
    valid_yaml = """
- name: Test task
  lineinfile:
    path: /etc/test
    line: "test=value"
"""

    # 非法的 YAML
    invalid_yaml = """
- name: Test task
  lineinfile:
    path: /etc/test
    line: "test=value"
  invalid_indent:
 - wrong
"""

    is_valid, error = validate_yaml(valid_yaml)
    print(f"合法 YAML 验证：{SUCCESS_MARK if is_valid else FAIL_MARK} 通过")

    is_valid, error = validate_yaml(invalid_yaml)
    print(f"非法 YAML 验证：{SUCCESS_MARK if not is_valid else FAIL_MARK} 正确识别")
    if error:
        print(f"  错误信息：{error[:100]}...")

    return True


def test_with_rag_results():
    """测试与 RAG 查询结果结合使用。"""
    print_separator("测试 3: RAG 查询 + 代码生成")

    try:
        # 尝试查询向量数据库
        querier = RAGQuerier()
        results = querier.query("SSH", n_results=2)

        if not results:
            print("向量数据库中无 SSH 相关数据，使用模拟数据测试")
            # 使用模拟数据
            from agent.rag_querier import QueryResult
            results = [
                QueryResult(
                    content="SSH configuration",
                    rule_id="1.1",
                    section_title="Ensure SSH root login is disabled",
                    cloud_provider="alibaba",
                    remediation="Disable root login in sshd_config",
                    page_number=10,
                    source_file="test.pdf",
                    distance=0.1
                )
            ]

        generator = CodeGenerator()

        for result in results:
            print(f"\n查询结果：{result.rule_id} - {result.section_title}")
            print(f"距离：{result.distance:.4f}")
            print("-" * 50)

            gen_result = generator.generate(
                rule_id=result.rule_id,
                section_title=result.section_title,
                cloud_provider=result.cloud_provider,
                remediation=result.remediation
            )

            if gen_result.success:
                print(f"✓ 代码生成成功")
                print("\n生成的 Ansible 代码:")
                print("-" * 50)
                # 重新生成 YAML 用于显示
                for task in gen_result.tasks:
                    print(f"- name: {task.name}")
                    print(f"  {task.module}:")
                    for k, v in task.params.items():
                        print(f"    {k}: {v}")
                    print()
            else:
                print(f"✗ 代码生成失败：{gen_result.error}")

        return True

    except Exception as e:
        print(f"测试跳过：{e}")
        return False


def test_batch_generation():
    """测试批量代码生成。"""
    print_separator("测试 4: 批量代码生成")

    test_rules = [
        ("1.1", "SSH 配置", "禁用 root 登录", "alibaba"),
        ("1.2", "SSH 配置", "设置 Protocol 2", "alibaba"),
        ("2.1", "日志审计", "启用 rsyslog", "tencent"),
        ("2.2", "日志审计", "配置 logrotate", "tencent"),
        ("3.1", "网络配置", "启用防火墙", "google"),
    ]

    generator = CodeGenerator()
    success_count = 0

    for rule_id, title, remediation, provider in test_rules:
        result = generator.generate(
            rule_id=rule_id,
            section_title=title,
            cloud_provider=provider,
            remediation=remediation
        )

        if result.success:
            success_count += 1
            status = SUCCESS_MARK
        else:
            status = FAIL_MARK

        print(f"{status} {rule_id}: {title} -> {len(result.tasks)} 个任务")

    print(f"\n总计：{success_count}/{len(test_rules)} 成功")
    return success_count == len(test_rules)


def test_convenience_function():
    """测试便捷函数。"""
    print_separator("测试 5: 便捷函数测试")

    result = generate_ansible_code(
        rule_id="1.1",
        section_title="测试规则",
        remediation="配置 SSH 安全设置",
        cloud_provider="alibaba"
    )

    print(f"规则：{result.rule_id}")
    print(f"成功：{result.success}")
    print(f"任务数：{len(result.tasks)}")
    print(f"模型：{result.model or '模拟模式'}")

    if result.success:
        for task in result.tasks:
            print(f"  - {task.name} ({task.module})")

    return result.success


def main():
    """运行所有测试。"""
    print_separator("阶段 2：语义翻译引擎测试")
    print(f"API Key 状态：{'已配置' if os.getenv('OPENAI_API_KEY') else '未配置 (使用模拟模式)'}")

    results = []

    # 运行测试
    results.append(("模拟模式生成", test_mock_generation()))
    results.append(("YAML 验证", test_yaml_validation()))
    results.append(("RAG 集成", test_with_rag_results()))
    results.append(("批量生成", test_batch_generation()))
    results.append(("便捷函数", test_convenience_function()))

    # 总结
    print_separator("测试总结")
    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = SUCCESS_MARK if result else FAIL_MARK
        print(f"  {status}: {name}")

    print(f"\n总计：{passed}/{total} 测试通过")

    if passed == total:
        print("\n[SUCCESS] 阶段 2 测试全部通过!")
        return 0
    else:
        print("\n[WARNING] 部分测试未通过，请检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
