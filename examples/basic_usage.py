<<<<<<< HEAD
#!/usr/bin/env python
"""使用示例 - 演示 Security Hardening Framework 的基本用法。

本脚本展示了如何使用安全加固框架的主要功能：
1. 知识入库（PDF 解析、向量化）
2. 知识检索（语义搜索）
3. 代码生成（LLM 转换）
4. 执行加固（Ansible）
5. 报告生成
"""

import sys
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def example_basic_usage():
    """基础使用示例。"""
    print("=" * 60)
    print("基础使用示例")
    print("=" * 60)

    from main_agent import SecurityHardeningAgent

    # 创建代理实例
    config = {
        "db_path": "./vector_db",
        "model_name": "all-MiniLM-L6-v2",
        "llm_model": "deepseek-chat",
        "playbook_dir": "./playbooks",
        "report_dir": "./reports",
        "audit_dir": "./audit_logs"
    }

    agent = SecurityHardeningAgent(config)
    print(f"✓ 代理初始化完成")
    print(f"  - LLM 可用：{agent.llm_client.is_available}")
    print(f"  - 数据库路径：{agent.knowledge_store.db_path}")

    return agent


def example_ingest_knowledge(agent):
    """知识入库示例。"""
    print("\n" + "=" * 60)
    print("知识入库示例")
    print("=" * 60)

    doc_dir = "./doc"
    if not Path(doc_dir).exists():
        print(f"⚠ 文档目录不存在：{doc_dir}")
        print("  跳过知识入库步骤")
        return

    print(f"正在处理文档：{doc_dir}")
    report = agent.ingest_knowledge(doc_dir)

    print(f"✓ 知识入库完成")
    print(f"  - 新增条目：{report.get('items_added', 0)}")
    print(f"  - 总条目数：{report.get('total_items', 0)}")


def example_search_knowledge(agent):
    """知识检索示例。"""
    print("\n" + "=" * 60)
    print("知识检索示例")
    print("=" * 60)

    queries = [
        "SSH configuration",
        "Access control",
        "Logging and auditing"
    ]

    for query in queries:
        print(f"\n搜索：{query}")
        results = agent.search_knowledge(query, n_results=3)

        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. [{result['score']:.2f}] {result['metadata'].get('source_file', 'N/A')}")
        else:
            print("  未找到相关结果")


def example_generate_playbook(agent):
    """Playbook 生成示例。"""
    print("\n" + "=" * 60)
    print("Playbook 生成示例")
    print("=" * 60)

    playbook = agent.generate_playbook(
        rule_id="1.1",
        section_title="Disable SSH Root Login",
        remediation="Configure SSH to disable root login",
        cloud_provider="Generic"
    )

    print("生成的 Playbook:")
    print("-" * 40)
    print(playbook[:500] + "..." if len(playbook) > 500 else playbook)


def example_harden(agent):
    """执行加固示例。"""
    print("\n" + "=" * 60)
    print("执行加固示例")
    print("=" * 60)

    print("注意：此步骤需要 Ansible 环境")
    print("在 Windows 上将以模拟模式运行")

    # 示例：执行 SSH 配置加固
    result = agent.harden(
        query="SSH security configuration",
        target_host="localhost",
        enable_self_heal=True
    )

    print(f"执行结果:")
    print(f"  - 成功：{result.get('success', False)}")
    print(f"  - 总任务数：{result.get('total', 0)}")

    if result.get('results'):
        for r in result['results']:
            status = "✓" if r['success'] else "✗"
            print(f"  {status} {r['rule_id']}: {r.get('output', 'N/A')[:50]}...")


def example_generate_report(agent):
    """报告生成示例。"""
    print("\n" + "=" * 60)
    print("报告生成示例")
    print("=" * 60)

    report_path = agent.generate_report("security_hardening_demo")
    print(f"✓ 报告已生成：{report_path}")


def example_get_stats(agent):
    """统计信息示例。"""
    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)

    stats = agent.get_stats()

    print(f"知识库统计:")
    kb_stats = stats.get('knowledge_base', {})
    print(f"  - 集合名称：{kb_stats.get('collection_name', 'N/A')}")
    print(f"  - 总条目数：{kb_stats.get('total_items', 0)}")

    print(f"\nLLM 状态:")
    print(f"  - 可用：{stats.get('llm_available', False)}")

    print(f"\n审计统计:")
    audit_stats = stats.get('audit_stats', {})
    print(f"  - 总操作数：{audit_stats.get('total_actions', 0)}")


def main():
    """主函数。"""
    print("\n" + "█" * 60)
    print("█  智能化系统动态安全加固框架 - 使用示例")
    print("█" * 60)

    try:
        # 1. 初始化代理
        agent = example_basic_usage()

        # 2. 知识入库（如果有文档）
        example_ingest_knowledge(agent)

        # 3. 知识检索
        example_search_knowledge(agent)

        # 4. Playbook 生成
        example_generate_playbook(agent)

        # 5. 执行加固（演示）
        example_harden(agent)

        # 6. 报告生成
        example_generate_report(agent)

        # 7. 统计信息
        example_get_stats(agent)

        print("\n" + "=" * 60)
        print("✓ 演示完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 错误：{e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
=======
#!/usr/bin/env python
"""使用示例 - 演示 Security Hardening Framework 的基本用法。

本脚本展示了如何使用安全加固框架的主要功能：
1. 知识入库（PDF 解析、向量化）
2. 知识检索（语义搜索）
3. 代码生成（LLM 转换）
4. 执行加固（Ansible）
5. 报告生成1
"""

import sys
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def example_basic_usage():
    """基础使用示例。"""
    print("=" * 60)
    print("基础使用示例")
    print("=" * 60)

    from main_agent import SecurityHardeningAgent

    # 创建代理实例
    config = {
        "db_path": "./vector_db",
        "model_name": "all-MiniLM-L6-v2",
        "llm_model": "deepseek-chat",
        "playbook_dir": "./playbooks",
        "report_dir": "./reports",
        "audit_dir": "./audit_logs"
    }

    agent = SecurityHardeningAgent(config)
    print(f"✓ 代理初始化完成")
    print(f"  - LLM 可用：{agent.llm_client.is_available}")
    print(f"  - 数据库路径：{agent.knowledge_store.db_path}")

    return agent


def example_ingest_knowledge(agent):
    """知识入库示例。"""
    print("\n" + "=" * 60)
    print("知识入库示例")
    print("=" * 60)

    doc_dir = "./doc"
    if not Path(doc_dir).exists():
        print(f"⚠ 文档目录不存在：{doc_dir}")
        print("  跳过知识入库步骤")
        return

    print(f"正在处理文档：{doc_dir}")
    report = agent.ingest_knowledge(doc_dir)

    print(f"✓ 知识入库完成")
    print(f"  - 新增条目：{report.get('items_added', 0)}")
    print(f"  - 总条目数：{report.get('total_items', 0)}")


def example_search_knowledge(agent):
    """知识检索示例。"""
    print("\n" + "=" * 60)
    print("知识检索示例")
    print("=" * 60)

    queries = [
        "SSH configuration",
        "Access control",
        "Logging and auditing"
    ]

    for query in queries:
        print(f"\n搜索：{query}")
        results = agent.search_knowledge(query, n_results=3)

        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. [{result['score']:.2f}] {result['metadata'].get('source_file', 'N/A')}")
        else:
            print("  未找到相关结果")


def example_generate_playbook(agent):
    """Playbook 生成示例。"""
    print("\n" + "=" * 60)
    print("Playbook 生成示例")
    print("=" * 60)

    playbook = agent.generate_playbook(
        rule_id="1.1",
        section_title="Disable SSH Root Login",
        remediation="Configure SSH to disable root login",
        cloud_provider="Generic"
    )

    print("生成的 Playbook:")
    print("-" * 40)
    print(playbook[:500] + "..." if len(playbook) > 500 else playbook)


def example_harden(agent):
    """执行加固示例。"""
    print("\n" + "=" * 60)
    print("执行加固示例")
    print("=" * 60)

    print("注意：此步骤需要 Ansible 环境")
    print("在 Windows 上将以模拟模式运行")

    # 示例：执行 SSH 配置加固
    result = agent.harden(
        query="SSH security configuration",
        target_host="localhost",
        enable_self_heal=True
    )

    print(f"执行结果:")
    print(f"  - 成功：{result.get('success', False)}")
    print(f"  - 总任务数：{result.get('total', 0)}")

    if result.get('results'):
        for r in result['results']:
            status = "✓" if r['success'] else "✗"
            print(f"  {status} {r['rule_id']}: {r.get('output', 'N/A')[:50]}...")


def example_generate_report(agent):
    """报告生成示例。"""
    print("\n" + "=" * 60)
    print("报告生成示例")
    print("=" * 60)

    report_path = agent.generate_report("security_hardening_demo")
    print(f"✓ 报告已生成：{report_path}")


def example_get_stats(agent):
    """统计信息示例。"""
    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)

    stats = agent.get_stats()

    print(f"知识库统计:")
    kb_stats = stats.get('knowledge_base', {})
    print(f"  - 集合名称：{kb_stats.get('collection_name', 'N/A')}")
    print(f"  - 总条目数：{kb_stats.get('total_items', 0)}")

    print(f"\nLLM 状态:")
    print(f"  - 可用：{stats.get('llm_available', False)}")

    print(f"\n审计统计:")
    audit_stats = stats.get('audit_stats', {})
    print(f"  - 总操作数：{audit_stats.get('total_actions', 0)}")


def main():
    """主函数。"""
    print("\n" + "█" * 60)
    print("█  智能化系统动态安全加固框架 - 使用示例")
    print("█" * 60)

    try:
        # 1. 初始化代理
        agent = example_basic_usage()

        # 2. 知识入库（如果有文档）
        example_ingest_knowledge(agent)

        # 3. 知识检索
        example_search_knowledge(agent)

        # 4. Playbook 生成
        example_generate_playbook(agent)

        # 5. 执行加固（演示）
        example_harden(agent)

        # 6. 报告生成
        example_generate_report(agent)

        # 7. 统计信息
        example_get_stats(agent)

        print("\n" + "=" * 60)
        print("✓ 演示完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 错误：{e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
