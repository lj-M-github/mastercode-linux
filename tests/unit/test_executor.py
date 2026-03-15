"""单元测试 - Executor 模块."""

import unittest
import sys
from pathlib import Path
import yaml
from unittest.mock import patch, MagicMock, mock_open

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from executor.ansible_runner import AnsibleRunner, ExecutionResult
from executor.playbook_builder import PlaybookBuilder, Task
from executor.ssh_client import SSHClient, SSHConfig, SSHResult


class TestExecutionResult(unittest.TestCase):
    """ExecutionResult 测试类。"""

    def test_str_success(self):
        """测试成功结果字符串表示。"""
        result = ExecutionResult(
            plan_id="1.1",
            success=True,
            steps_executed=5,
            steps_failed=0,
            output="ok=5"
        )
        self.assertIn("SUCCESS", str(result))

    def test_str_failure(self):
        """测试失败结果字符串表示。"""
        result = ExecutionResult(
            plan_id="1.1",
            success=False,
            steps_executed=0,
            steps_failed=2,
            output=""
        )
        self.assertIn("FAILED", str(result))


class TestAnsibleRunner(unittest.TestCase):
    """AnsibleRunner 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.runner = AnsibleRunner()

    @patch('executor.ansible_runner.Path.exists')
    def test_run_playbook_not_found(self, mock_exists):
        """测试剧本不存在。"""
        mock_exists.return_value = False
        result = self.runner.run_playbook("nonexistent.yml")
        self.assertFalse(result.success)
        self.assertIn("不存在", result.error)

    @patch('executor.ansible_runner.subprocess.run')
    @patch('executor.ansible_runner.Path.exists')
    def test_run_playbook_success(self, mock_exists, mock_run):
        """测试剧本执行成功。"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ok=5 changed=2",
            stderr=""
        )
        result = self.runner.run_playbook("test.yml")
        self.assertTrue(result.success)

    def test_count_successful_steps(self):
        """测试统计成功步骤。"""
        output = "ok=1 changed=1 failed=0"
        count = self.runner._count_successful_steps(output)
        self.assertEqual(count, 2)

    def test_count_failed_steps(self):
        """测试统计失败步骤。"""
        output = "ok=1 failed=1 unreachable=1"
        count = self.runner._count_failed_steps(output)
        self.assertEqual(count, 2)

    @patch('executor.ansible_runner.AnsibleRunner.run_playbook')
    def test_execute_passes_target_host_as_limit(self, mock_run_playbook):
        """测试 execute 会把 target_host 透传为 --limit。"""
        mock_run_playbook.return_value = ExecutionResult(
            plan_id="tmp.yml",
            success=True,
            steps_executed=1,
            steps_failed=0,
            output="ok=1"
        )
        _ = self.runner.execute("- hosts: all\n  tasks: []\n", target_host="web")
        self.assertTrue(mock_run_playbook.called)
        self.assertEqual(mock_run_playbook.call_args.kwargs.get("limit"), "web")


class TestPlaybookBuilder(unittest.TestCase):
    """PlaybookBuilder 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.builder = PlaybookBuilder("Test Playbook", "all")

    def test_add_task(self):
        """测试添加任务。"""
        self.builder.add_task(
            name="Test task",
            module="command",
            params={"cmd": "echo hello"}
        )
        self.assertEqual(len(self.builder.tasks), 1)

    def test_add_task_chain(self):
        """测试链式调用添加任务。"""
        self.builder.add_task("Task 1", "command").add_task("Task 2", "debug")
        self.assertEqual(len(self.builder.tasks), 2)

    def test_build(self):
        """测试构建 Playbook。"""
        self.builder.add_task("Test", "command", {"cmd": "echo test"})
        playbook = self.builder.build()
        self.assertIn("Test Playbook", playbook)
        self.assertIn("Test", playbook)

    def test_build_outputs_play_list(self):
        """测试 build 输出为 play 列表结构。"""
        self.builder.add_task("Test", "command", {"cmd": "echo test"})
        playbook = self.builder.build()
        data = yaml.safe_load(playbook)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Test Playbook")

    def test_task_to_dict(self):
        """测试 Task 转字典。"""
        task = Task(
            name="Test",
            module="command",
            params={"cmd": "test"},
            when="ansible_os_family == 'RedHat'",
            register="result"
        )
        task_dict = task.to_dict()
        self.assertEqual(task_dict["name"], "Test")
        self.assertEqual(task_dict["when"], "ansible_os_family == 'RedHat'")
        self.assertEqual(task_dict["register"], "result")


class TestSSHConfig(unittest.TestCase):
    """SSHConfig 测试类。"""

    def test_default_values(self):
        """测试默认值。"""
        config = SSHConfig(host="192.168.1.1")
        self.assertEqual(config.port, 22)
        self.assertEqual(config.timeout, 30)


class TestSSHClient(unittest.TestCase):
    """SSHClient 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.config = SSHConfig(host="192.168.1.1", username="test")
        self.client = SSHClient(self.config)

    def test_initial_state(self):
        """测试初始状态。"""
        self.assertFalse(self.client.is_connected)

    def test_disconnect(self):
        """测试断开连接。"""
        self.client._connected = True
        self.client.disconnect()
        self.assertFalse(self.client.is_connected)

    @patch('executor.ssh_client.subprocess.run')
    def test_execute_not_connected(self, mock_run):
        """测试未连接时执行。"""
        # SSHClient.execute 会先尝试连接
        mock_run.return_value = MagicMock(returncode=0, stdout="Connection successful", stderr="")
        result = self.client.execute("test")
        # 连接成功后执行命令，命令返回成功
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
