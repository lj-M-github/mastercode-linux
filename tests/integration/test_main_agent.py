"""集成测试 - Main Agent."""

from unittest.mock import patch, MagicMock
import pytest

from src.main_agent import SecurityHardeningAgent
from src.feedback.self_heal import HealingResult


class TestSecurityHardeningAgent:
    """SecurityHardeningAgent 测试类。"""

    @pytest.fixture
    def agent(self):
        """测试前准备。"""
        with patch('src.main_agent.KnowledgeStore') as mock_store, \
             patch('src.main_agent.LLMClient') as mock_llm, \
             patch('src.main_agent.AnsibleRunner') as mock_runner:
            # 模拟各组件
            mock_store_instance = MagicMock()
            mock_store_instance.get_stats.return_value = {"total_items": 0}
            mock_store.return_value = mock_store_instance

            mock_llm_instance = MagicMock()
            mock_llm_instance.is_available = False
            mock_llm.return_value = mock_llm_instance

            mock_runner_instance = MagicMock()
            mock_runner.return_value = mock_runner_instance

            config = {
                "db_path": "./test_vector_db",
                "model_name": "test-model",
                "llm_model": "deepseek-chat",
                "playbook_dir": "./test_playbooks",
                "report_dir": "./test_reports",
                "audit_dir": "./test_audit"
            }
            return SecurityHardeningAgent(config)

    def test_init(self, agent):
        """测试初始化。"""
        assert agent.knowledge_store is not None
        assert agent.llm_client is not None
        assert agent.executor is not None

    @patch('src.main_agent.Path.glob')
    def test_ingest_knowledge(self, mock_glob, agent):
        """测试知识入库。"""
        mock_glob.return_value = []  # 没有 PDF 文件
        # 设置 knowledge_store.add 返回 0（没有添加任何内容）
        agent.knowledge_store.add = MagicMock(return_value=0)
        agent.knowledge_store.get_stats = MagicMock(return_value={"total_items": 0})

        result = agent.ingest_knowledge("./test_docs")

        assert "doc_dir" in result
        assert "items_added" in result
        assert result["items_added"] == 0

    def test_search_knowledge_no_filter(self, agent):
        """测试搜索知识（无过滤）。"""
        agent.knowledge_store.search = MagicMock(return_value=[])
        results = agent.search_knowledge("SSH config")
        assert results == []

    def test_search_knowledge_with_filter(self, agent):
        """测试搜索知识（带过滤）。"""
        agent.knowledge_store.search = MagicMock(return_value=[])
        results = agent.search_knowledge(
            "SSH config",
            n_results=10,
            cloud_provider="Aliyun"
        )
        assert results == []

    def test_generate_playbook_mock(self, agent):
        """测试生成模拟 Playbook。"""
        playbook = agent.generate_playbook(
            rule_id="1.1",
            section_title="Test",
            remediation="Disable root login",
            cloud_provider="test"
        )
        assert "1.1" in playbook
        assert "localhost" in playbook

    def test_extract_yaml_accepts_raw_yaml(self, agent):
        """测试主代理可直接接受未包裹代码块的原始 YAML。"""
        raw_yaml = """---
- name: Test play
  hosts: localhost
  tasks:
    - name: Ping
      ping:
"""
        extracted = agent._extract_yaml(raw_yaml)
        assert extracted == raw_yaml.strip()

    def test_generate_playbook_uses_raw_yaml_response(self, agent):
        """测试 LLM 返回原始 YAML 时不会退回 mock playbook。"""
        agent.llm_client.is_available = True
        agent.llm_client.generate = MagicMock(
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
        playbook = agent.generate_playbook("1.1", "Test", "Do something")
        assert "Generated play" in playbook
        assert "Apply remediation" not in playbook

    def test_harden_no_results(self, agent):
        """测试加固无结果。"""
        agent.search_knowledge = MagicMock(return_value=[])
        result = agent.harden("SSH config")
        assert result["success"] is False
        assert result["error"] == "No relevant rules found"

    def test_harden_uses_heal_execution_result_without_rerun(self, agent):
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
        agent.search_knowledge = MagicMock(return_value=[{
            "content": fake_result.content,
            "metadata": fake_result.metadata,
            "score": fake_result.score,
            "rank": fake_result.rank
        }])

        # 2) 首次执行失败
        first_exec = MagicMock(success=False, output="", error="fatal: failed")
        agent.executor.execute = MagicMock(return_value=first_exec)

        # 3) 自愈返回成功并携带已执行结果
        healed_exec = MagicMock(success=True, output="ok=1", error="")
        agent.self_healer.heal = MagicMock(return_value=HealingResult(
            success=True,
            rewritten_playbook="- hosts: localhost\n  tasks: []",
            attempts=1,
            execution_result=healed_exec
        ))

        result = agent.harden("ssh")
        assert result["success"] is True
        assert agent.executor.execute.call_count == 1

    def test_get_stats(self, agent):
        """测试获取统计信息。"""
        stats = agent.get_stats()
        assert "knowledge_base" in stats
        assert "llm_available" in stats

    def test_generate_report(self, agent):
        """测试生成报告。"""
        agent.report_generator.generate = MagicMock(
            return_value="./test_reports/report.json"
        )
        report_path = agent.generate_report("test")
        assert report_path == "./test_reports/report.json"
