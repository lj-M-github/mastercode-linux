"""单元测试 - Executor 模块."""

import yaml
from unittest.mock import patch, MagicMock, mock_open
import pytest

from src.executor.ansible_runner import AnsibleRunner, ExecutionResult
from src.executor.playbook_builder import PlaybookBuilder, Task
from src.executor.ssh_client import SSHClient, SSHConfig, SSHResult


class TestExecutionResult:
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
        assert "SUCCESS" in str(result)

    def test_str_failure(self):
        """测试失败结果字符串表示。"""
        result = ExecutionResult(
            plan_id="1.1",
            success=False,
            steps_executed=0,
            steps_failed=2,
            output=""
        )
        assert "FAILED" in str(result)


class TestAnsibleRunner:
    """AnsibleRunner 测试类。"""

    @pytest.fixture
    def runner(self):
        """测试前准备。"""
        return AnsibleRunner()

    @patch('src.executor.ansible_runner.Path.exists')
    def test_run_playbook_not_found(self, mock_exists, runner):
        """测试剧本不存在。"""
        mock_exists.return_value = False
        result = runner.run_playbook("nonexistent.yml")
        assert not result.success
        assert "不存在" in result.error

    @patch('src.executor.ansible_runner.subprocess.run')
    @patch('src.executor.ansible_runner.Path.exists')
    def test_run_playbook_success(self, mock_exists, mock_run, runner):
        """测试剧本执行成功。"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ok=5 changed=2",
            stderr=""
        )
        result = runner.run_playbook("test.yml")
        assert result.success

    def test_count_successful_steps(self, runner):
        """测试统计成功步骤。"""
        output = "ok=1 changed=1 failed=0"
        count = runner._count_successful_steps(output)
        assert count == 2

    def test_count_failed_steps(self, runner):
        """测试统计失败步骤。"""
        output = "ok=1 failed=1 unreachable=1"
        count = runner._count_failed_steps(output)
        assert count == 2

    @patch('src.executor.ansible_runner.AnsibleRunner.run_playbook')
    def test_execute_passes_target_host_as_limit(self, mock_run_playbook, runner):
        """测试 execute 会把 target_host 透传为 --limit。"""
        mock_run_playbook.return_value = ExecutionResult(
            plan_id="tmp.yml",
            success=True,
            steps_executed=1,
            steps_failed=0,
            output="ok=1"
        )
        runner.execute("- hosts: all\n  tasks: []\n", target_host="web")
        assert mock_run_playbook.called
        assert mock_run_playbook.call_args.kwargs.get("limit") == "web"


class TestPlaybookBuilder:
    """PlaybookBuilder 测试类。"""

    @pytest.fixture
    def builder(self):
        """测试前准备。"""
        return PlaybookBuilder("Test Playbook", "all")

    def test_add_task(self, builder):
        """测试添加任务。"""
        builder.add_task(
            name="Test task",
            module="command",
            params={"cmd": "echo hello"}
        )
        assert len(builder.tasks) == 1

    def test_add_task_chain(self, builder):
        """测试链式调用添加任务。"""
        builder.add_task("Task 1", "command").add_task("Task 2", "debug")
        assert len(builder.tasks) == 2

    def test_build(self, builder):
        """测试构建 Playbook。"""
        builder.add_task("Test", "command", {"cmd": "echo test"})
        playbook = builder.build()
        assert "Test Playbook" in playbook
        assert "Test" in playbook

    def test_build_outputs_play_list(self, builder):
        """测试 build 输出为 play 列表结构。"""
        builder.add_task("Test", "command", {"cmd": "echo test"})
        playbook = builder.build()
        data = yaml.safe_load(playbook)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Test Playbook"

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
        assert task_dict["name"] == "Test"
        assert task_dict["when"] == "ansible_os_family == 'RedHat'"
        assert task_dict["register"] == "result"


class TestSSHConfig:
    """SSHConfig 测试类。"""

    def test_default_values(self):
        """测试默认值。"""
        config = SSHConfig(host="192.168.1.1")
        assert config.port == 22
        assert config.timeout == 30


class TestSSHClient:
    """SSHClient 测试类。"""

    @pytest.fixture
    def client(self):
        """测试前准备。"""
        config = SSHConfig(host="192.168.1.1", username="test")
        return SSHClient(config)

    def test_initial_state(self, client):
        """测试初始状态。"""
        assert not client.is_connected

    def test_disconnect(self, client):
        """测试断开连接。"""
        client._connected = True
        client.disconnect()
        assert not client.is_connected

    @patch('src.executor.ssh_client.subprocess.run')
    def test_execute_not_connected(self, mock_run, client):
        """测试未连接时执行。"""
        # SSHClient.execute 会先尝试连接
        mock_run.return_value = MagicMock(returncode=0, stdout="Connection successful", stderr="")
        result = client.execute("test")
        # 连接成功后执行命令，命令返回成功
        assert result.success
