<<<<<<< HEAD
"""集成测试 - Main Agent."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from main_agent import SecurityHardeningAgent
from feedback.self_heal import HealingResult


class TestSecurityHardeningAgent(unittest.TestCase):
    """SecurityHardeningAgent 测试类。"""

    @patch('main_agent.KnowledgeStore')
    @patch('main_agent.LLMClient')
    @patch('main_agent.AnsibleRunner')
    def setUp(self, mock_runner, mock_llm, mock_store):
        """测试前准备。"""
        # 模拟各组件
        mock_store_instance = MagicMock()
        mock_store_instance.get_stats.return_value = {"total_items": 0}
        mock_store.return_value = mock_store_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.is_available = False
        mock_llm.return_value = mock_llm_instance

        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance

        self.config = {
            "db_path": "./test_vector_db",
            "model_name": "test-model",
            "llm_model": "deepseek-chat",
            "playbook_dir": "./test_playbooks",
            "report_dir": "./test_reports",
            "audit_dir": "./test_audit"
        }
        self.agent = SecurityHardeningAgent(self.config)

    def test_init(self):
        """测试初始化。"""
        self.assertIsNotNone(self.agent.knowledge_store)
        self.assertIsNotNone(self.agent.llm_client)
        self.assertIsNotNone(self.agent.executor)

    @patch('main_agent.Path.glob')
    def test_ingest_knowledge(self, mock_glob):
        """测试知识入库。"""
        mock_glob.return_value = []  # 没有 PDF 文件
        # 设置 knowledge_store.add 返回 0（没有添加任何内容）
        self.agent.knowledge_store.add = MagicMock(return_value=0)
        self.agent.knowledge_store.get_stats = MagicMock(return_value={"total_items": 0})

        result = self.agent.ingest_knowledge("./test_docs")

        self.assertIn("doc_dir", result)
        self.assertIn("items_added", result)
        self.assertEqual(result["items_added"], 0)

    def test_search_knowledge_no_filter(self):
        """测试搜索知识（无过滤）。"""
        self.agent.knowledge_store.search = MagicMock(return_value=[])
        results = self.agent.search_knowledge("SSH config")
        self.assertEqual(results, [])

    def test_search_knowledge_with_filter(self):
        """测试搜索知识（带过滤）。"""
        self.agent.knowledge_store.search = MagicMock(return_value=[])
        results = self.agent.search_knowledge(
            "SSH config",
            n_results=10,
            cloud_provider="Aliyun"
        )
        self.assertEqual(results, [])

    def test_generate_playbook_mock(self):
        """测试生成模拟 Playbook。"""
        playbook = self.agent.generate_playbook(
            rule_id="1.1",
            section_title="Test",
            remediation="Disable root login",
            cloud_provider="test"
        )
        self.assertIn("1.1", playbook)
        self.assertIn("localhost", playbook)

    def test_extract_yaml_accepts_raw_yaml(self):
        """测试主代理可直接接受未包裹代码块的原始 YAML。"""
        raw_yaml = """---
- name: Test play
  hosts: localhost
  tasks:
    - name: Ping
      ping:
"""
        extracted = self.agent._extract_yaml(raw_yaml)
        self.assertEqual(extracted, raw_yaml.strip())

    def test_generate_playbook_uses_raw_yaml_response(self):
        """测试 LLM 返回原始 YAML 时不会退回 mock playbook。"""
        self.agent.llm_client.is_available = True
        self.agent.llm_client.generate = MagicMock(
            return_value=MagicMock(
                content="""---
- name: Generated play
  hosts: localhost
  tasks:
    - name: Run command
      command: echo ok
"""
            )
        )
        playbook = self.agent.generate_playbook("1.1", "Test", "Do something")
        self.assertIn("Generated play", playbook)
        self.assertNotIn("Apply remediation", playbook)

    def test_harden_no_results(self):
        """测试加固无结果。"""
        self.agent.search_knowledge = MagicMock(return_value=[])
        result = self.agent.harden("SSH config")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "No relevant rules found")

    def test_harden_uses_heal_execution_result_without_rerun(self):
        """自愈成功且带 execution_result 时，不应重复执行 playbook。"""
        # 1) 准备检索结果
        fake_result = MagicMock()
        fake_result.content = "content"
        fake_result.metadata = {
            "rule_id": "1.1",
            "section_title": "title",
            "remediation": "remediation",
            "cloud_provider": "test"
        }
        fake_result.score = 0.9
        fake_result.rank = 1
        self.agent.search_knowledge = MagicMock(return_value=[{
            "content": fake_result.content,
            "metadata": fake_result.metadata,
            "score": fake_result.score,
            "rank": fake_result.rank
        }])

        # 2) 首次执行失败
        first_exec = MagicMock(success=False, output="", error="fatal: failed")
        self.agent.executor.execute = MagicMock(return_value=first_exec)

        # 3) 自愈返回成功并携带已执行结果
        healed_exec = MagicMock(success=True, output="ok=1", error="")
        self.agent.self_healer.heal = MagicMock(return_value=HealingResult(
            success=True,
            rewritten_playbook="- hosts: localhost\n  tasks: []",
            attempts=1,
            execution_result=healed_exec
        ))

        result = self.agent.harden("ssh")
        self.assertTrue(result["success"])
        self.assertEqual(self.agent.executor.execute.call_count, 1)

    def test_get_stats(self):
        """测试获取统计信息。"""
        stats = self.agent.get_stats()
        self.assertIn("knowledge_base", stats)
        self.assertIn("llm_available", stats)

    def test_generate_report(self):
        """测试生成报告。"""
        self.agent.report_generator.generate = MagicMock(
            return_value="./test_reports/report.json"
        )
        report_path = self.agent.generate_report("test")
        self.assertEqual(report_path, "./test_reports/report.json")


if __name__ == "__main__":
    unittest.main()
=======
"""集成测试 - Main Agent."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from main_agent import SecurityHardeningAgent
from feedback.self_heal import HealingResult


class TestSecurityHardeningAgent(unittest.TestCase):
    """SecurityHardeningAgent 测试类。"""

    @patch('main_agent.KnowledgeStore')
    @patch('main_agent.LLMClient')
    @patch('main_agent.AnsibleRunner')
    def setUp(self, mock_runner, mock_llm, mock_store):
        """测试前准备。"""
        # 模拟各组件
        mock_store_instance = MagicMock()
        mock_store_instance.get_stats.return_value = {"total_items": 0}
        mock_store.return_value = mock_store_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.is_available = False
        mock_llm.return_value = mock_llm_instance

        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance

        self.config = {
            "db_path": "./test_vector_db",
            "model_name": "test-model",
            "llm_model": "gpt-3.5-turbo",
            "playbook_dir": "./test_playbooks",
            "report_dir": "./test_reports",
            "audit_dir": "./test_audit"
        }
        self.agent = SecurityHardeningAgent(self.config)

    def test_init(self):
        """测试初始化。"""
        self.assertIsNotNone(self.agent.knowledge_store)
        self.assertIsNotNone(self.agent.llm_client)
        self.assertIsNotNone(self.agent.executor)

    @patch('main_agent.Path.glob')
    def test_ingest_knowledge(self, mock_glob):
        """测试知识入库。"""
        mock_glob.return_value = []  # 没有 PDF 文件
        # 设置 knowledge_store.add 返回 0（没有添加任何内容）
        self.agent.knowledge_store.add = MagicMock(return_value=0)
        self.agent.knowledge_store.get_stats = MagicMock(return_value={"total_items": 0})

        result = self.agent.ingest_knowledge("./test_docs")

        self.assertIn("doc_dir", result)
        self.assertIn("items_added", result)
        self.assertEqual(result["items_added"], 0)

    def test_search_knowledge_no_filter(self):
        """测试搜索知识（无过滤）。"""
        self.agent.knowledge_store.search = MagicMock(return_value=[])
        results = self.agent.search_knowledge("SSH config")
        self.assertEqual(results, [])

    def test_search_knowledge_with_filter(self):
        """测试搜索知识（带过滤）。"""
        self.agent.knowledge_store.search = MagicMock(return_value=[])
        results = self.agent.search_knowledge(
            "SSH config",
            n_results=10,
            cloud_provider="Aliyun"
        )
        self.assertEqual(results, [])

    def test_generate_playbook_mock(self):
        """测试生成模拟 Playbook。"""
        playbook = self.agent.generate_playbook(
            rule_id="1.1",
            section_title="Test",
            remediation="Disable root login",
            cloud_provider="test"
        )
        self.assertIn("1.1", playbook)
        self.assertIn("localhost", playbook)

    def test_extract_yaml_accepts_raw_yaml(self):
        """测试主代理可直接接受未包裹代码块的原始 YAML。"""
        raw_yaml = """---
- name: Test play
  hosts: localhost
  tasks:
    - name: Ping
      ping:
"""
        extracted = self.agent._extract_yaml(raw_yaml)
        self.assertEqual(extracted, raw_yaml.strip())

    def test_generate_playbook_uses_raw_yaml_response(self):
        """测试 LLM 返回原始 YAML 时不会退回 mock playbook。"""
        self.agent.llm_client.is_available = True
        self.agent.llm_client.generate = MagicMock(
            return_value=MagicMock(
                content="""---
- name: Generated play
  hosts: localhost
  tasks:
    - name: Run command
      command: echo ok
"""
            )
        )
        playbook = self.agent.generate_playbook("1.1", "Test", "Do something")
        self.assertIn("Generated play", playbook)
        self.assertNotIn("Apply remediation", playbook)

    def test_harden_no_results(self):
        """测试加固无结果。"""
        self.agent.search_knowledge = MagicMock(return_value=[])
        result = self.agent.harden("SSH config")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "No relevant rules found")

    def test_harden_uses_heal_execution_result_without_rerun(self):
        """自愈成功且带 execution_result 时，不应重复执行 playbook。"""
        # 1) 准备检索结果
        fake_result = MagicMock()
        fake_result.content = "content"
        fake_result.metadata = {
            "rule_id": "1.1",
            "section_title": "title",
            "remediation": "remediation",
            "cloud_provider": "test"
        }
        fake_result.score = 0.9
        fake_result.rank = 1
        self.agent.search_knowledge = MagicMock(return_value=[{
            "content": fake_result.content,
            "metadata": fake_result.metadata,
            "score": fake_result.score,
            "rank": fake_result.rank
        }])

        # 2) 首次执行失败
        first_exec = MagicMock(success=False, output="", error="fatal: failed")
        self.agent.executor.execute = MagicMock(return_value=first_exec)

        # 3) 自愈返回成功并携带已执行结果
        healed_exec = MagicMock(success=True, output="ok=1", error="")
        self.agent.self_healer.heal = MagicMock(return_value=HealingResult(
            success=True,
            rewritten_playbook="- hosts: localhost\n  tasks: []",
            attempts=1,
            execution_result=healed_exec
        ))

        result = self.agent.harden("ssh")
        self.assertTrue(result["success"])
        self.assertEqual(self.agent.executor.execute.call_count, 1)

    def test_get_stats(self):
        """测试获取统计信息。"""
        stats = self.agent.get_stats()
        self.assertIn("knowledge_base", stats)
        self.assertIn("llm_available", stats)

    def test_generate_report(self):
        """测试生成报告。"""
        self.agent.report_generator.generate = MagicMock(
            return_value="./test_reports/report.json"
        )
        report_path = self.agent.generate_report("test")
        self.assertEqual(report_path, "./test_reports/report.json")


if __name__ == "__main__":
    unittest.main()
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
