<<<<<<< HEAD
"""单元测试 - Feedback 模块."""

import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from feedback.result_parser import ResultParser, ExecutionResult
from feedback.error_analyzer import ErrorAnalyzer, ErrorAnalysis
from feedback.self_heal import SelfHealer, HealingResult


class TestExecutionResult(unittest.TestCase):
    """ExecutionResult 测试类。"""

    def test_to_dict(self):
        """测试转字典。"""
        result = ExecutionResult(
            task_id="1.1",
            success=True,
            steps_executed=5,
            steps_failed=0,
            output="ok=5",
            duration=10.5
        )
        result_dict = result.to_dict()
        self.assertEqual(result_dict["task_id"], "1.1")
        self.assertEqual(result_dict["success"], True)


class TestResultParser(unittest.TestCase):
    """ResultParser 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.parser = ResultParser()

    def test_parse_success(self):
        """测试解析成功结果。"""
        output = "ok=3 changed=2"
        result = self.parser.parse(output, "1.1")
        # _determine_success 检查 failed=和 unreachable=的出现次数
        # output 中没有这些字符串，所以 failed_count=0，success=True
        self.assertTrue(result.success)
        self.assertEqual(result.steps_executed, 5)  # ok=3 + changed=2

    def test_parse_success_with_zero_failure_fields(self):
        """failed=0 和 unreachable=0 不应被视为失败。"""
        output = "ok=3 changed=2 failed=0 unreachable=0"
        result = self.parser.parse(output, "1.1")
        self.assertTrue(result.success)
        self.assertEqual(result.steps_failed, 0)
        self.assertEqual(result.steps_executed, 5)

    def test_parse_failure(self):
        """测试解析失败结果。"""
        output = "ok=3 failed=1 unreachable=1"
        result = self.parser.parse(output, "1.1")
        self.assertFalse(result.success)
        self.assertEqual(result.steps_failed, 2)

    def test_parse_failure_without_recap_but_with_failure_signal(self):
        """无 recap 时，出现明确失败信号不能判定为成功。"""
        output = "fatal: [localhost]: FAILED! => permission denied"
        result = self.parser.parse(output, "1.1")
        self.assertFalse(result.success)

    def test_get_feedback_dict(self):
        """测试获取反馈字典。"""
        result = ExecutionResult(
            task_id="1.1",
            success=True,
            steps_executed=5,
            steps_failed=0,
            output=""
        )
        feedback = self.parser.get_feedback_dict(result)
        self.assertIn("success", feedback)
        self.assertIn("timestamp", feedback)


class TestErrorAnalyzer(unittest.TestCase):
    """ErrorAnalyzer 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.analyzer = ErrorAnalyzer()

    def test_classify_syntax_error(self):
        """测试分类语法错误。"""
        error_type = self.analyzer._classify_error("YAML syntax error")
        self.assertEqual(error_type, "syntax")

    def test_classify_connection_error(self):
        """测试分类连接错误。"""
        error_type = self.analyzer._classify_error("Connection failed")
        self.assertEqual(error_type, "connection")

    def test_classify_permission_error(self):
        """测试分类权限错误。"""
        error_type = self.analyzer._classify_error("Permission denied")
        self.assertEqual(error_type, "permission")

    def test_analyze_basic(self):
        """测试基础分析。"""
        analysis = self.analyzer.analyze("failed=2")
        self.assertIsInstance(analysis, ErrorAnalysis)
        self.assertIn(analysis.error_type, ["syntax", "connection", "permission", "command", "logic"])

    def test_get_common_cause(self):
        """测试获取常见原因。"""
        cause = self.analyzer._get_common_cause("syntax", "error")
        self.assertIn("YAML", cause)

    def test_get_suggestion(self):
        """测试获取建议。"""
        suggestion = self.analyzer._get_suggestion("connection")
        self.assertIsNotNone(suggestion)


class TestSelfHealer(unittest.TestCase):
    """SelfHealer 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.mock_llm = MagicMock()
        self.healer = SelfHealer(llm_client=self.mock_llm, max_retries=3)

    def test_can_retry(self):
        """测试是否可重试。"""
        self.assertTrue(self.healer.can_retry("syntax error"))
        self.assertFalse(self.healer.can_retry("invalid credentials"))

    def test_extract_yaml_from_code_block(self):
        """测试从代码块提取 YAML。"""
        text = """Here is the fixed playbook:
```yaml
- name: Test
  hosts: localhost
```
"""
        yaml = self.healer._extract_yaml(text)
        self.assertIn("- name: Test", yaml)

    def test_extract_yaml_plain(self):
        """测试提取纯 YAML。"""
        text = "- name: Test\n  hosts: localhost"
        yaml = self.healer._extract_yaml(text)
        self.assertIn("- name: Test", yaml)

    def test_extract_yaml_rejects_plain_explanation(self):
        """测试纯说明文字不会被当作 YAML 返回。"""
        text = "Here is the fixed playbook with some explanation only."
        yaml = self.healer._extract_yaml(text)
        self.assertEqual(yaml, "")

    def test_is_fixed(self):
        """测试判断是否已修复。"""
        analysis = ErrorAnalysis(
            error_type="syntax",
            error_message="error",
            root_cause="fixed",
            suggestion="The issue has been fixed",
            severity="high"
        )
        self.assertTrue(self.healer._is_fixed(analysis))

    def test_heal_no_llm(self):
        """测试无 LLM 时自愈。"""
        healer = SelfHealer(llm_client=None)
        result = healer.heal("playbook", "error")
        self.assertFalse(result.success)

    def test_rewrite_playbook_uses_error_log_in_prompt(self):
        """测试重写时会把错误日志注入 execution_log。"""
        self.mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- name: fixed\n  hosts: localhost\n```"""
        )

        _ = self.healer._rewrite_playbook(
            playbook="- name: old",
            failure_reason="syntax issue",
            execution_log="fatal: permission denied",
            original_rule="rule"
        )

        sent_prompt = self.mock_llm.generate.call_args.args[0]
        self.assertIn("fatal: permission denied", sent_prompt)

    def test_heal_stops_on_non_retryable_error(self):
        """不可重试错误应立即停止，不调用 LLM 重写。"""
        execute_fn = MagicMock()
        result = self.healer.heal(
            original_playbook="- hosts: localhost",
            error_log="authentication failed",
            original_rule="rule",
            execute_fn=execute_fn
        )
        self.assertFalse(result.success)
        self.assertEqual(self.mock_llm.generate.call_count, 0)
        self.assertEqual(result.attempts, 0)
        self.assertEqual(execute_fn.call_count, 0)

    def test_heal_returns_execution_result_on_success(self):
        """成功时应回传 execute_fn 的执行结果，供上层复用。"""
        self.mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- hosts: localhost\n  tasks: []\n```"""
        )
        retry_result = MagicMock(success=True, output="ok=1", error="")
        result = self.healer.heal(
            original_playbook="- hosts: localhost",
            error_log="fatal: something failed",
            original_rule="rule",
            execute_fn=lambda _: retry_result
        )
        self.assertTrue(result.success)
        self.assertIs(result.execution_result, retry_result)

    def test_heal_failed_attempt_count_matches_real_retries(self):
        """失败场景 attempts 应等于真实重写次数，而不是 max_retries 常量。"""
        self.mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- hosts: localhost\n  tasks: []\n```"""
        )

        failed_retry = MagicMock(success=False, output="", error="fatal: still failed")
        result = self.healer.heal(
            original_playbook="- hosts: localhost",
            error_log="fatal: first failed",
            original_rule="rule",
            execute_fn=lambda _: failed_retry
        )

        self.assertFalse(result.success)
        self.assertEqual(result.attempts, self.healer.max_retries)

    def test_get_healing_stats(self):
        """测试获取统计信息。"""
        results = [
            HealingResult(success=True, attempts=1),
            HealingResult(success=False, attempts=3)
        ]
        stats = self.healer.get_healing_stats(results)
        self.assertEqual(stats["total_attempts"], 2)
        self.assertEqual(stats["successful_healings"], 1)


if __name__ == "__main__":
    unittest.main()
=======
"""单元测试 - Feedback 模块."""

import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from feedback.result_parser import ResultParser, ExecutionResult
from feedback.error_analyzer import ErrorAnalyzer, ErrorAnalysis
from feedback.self_heal import SelfHealer, HealingResult


class TestExecutionResult(unittest.TestCase):
    """ExecutionResult 测试类。"""

    def test_to_dict(self):
        """测试转字典。"""
        result = ExecutionResult(
            task_id="1.1",
            success=True,
            steps_executed=5,
            steps_failed=0,
            output="ok=5",
            duration=10.5
        )
        result_dict = result.to_dict()
        self.assertEqual(result_dict["task_id"], "1.1")
        self.assertEqual(result_dict["success"], True)


class TestResultParser(unittest.TestCase):
    """ResultParser 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.parser = ResultParser()

    def test_parse_success(self):
        """测试解析成功结果。"""
        output = "ok=3 changed=2"
        result = self.parser.parse(output, "1.1")
        # _determine_success 检查 failed=和 unreachable=的出现次数
        # output 中没有这些字符串，所以 failed_count=0，success=True
        self.assertTrue(result.success)
        self.assertEqual(result.steps_executed, 5)  # ok=3 + changed=2

    def test_parse_success_with_zero_failure_fields(self):
        """failed=0 和 unreachable=0 不应被视为失败。"""
        output = "ok=3 changed=2 failed=0 unreachable=0"
        result = self.parser.parse(output, "1.1")
        self.assertTrue(result.success)
        self.assertEqual(result.steps_failed, 0)
        self.assertEqual(result.steps_executed, 5)

    def test_parse_failure(self):
        """测试解析失败结果。"""
        output = "ok=3 failed=1 unreachable=1"
        result = self.parser.parse(output, "1.1")
        self.assertFalse(result.success)
        self.assertEqual(result.steps_failed, 2)

    def test_parse_failure_without_recap_but_with_failure_signal(self):
        """无 recap 时，出现明确失败信号不能判定为成功。"""
        output = "fatal: [localhost]: FAILED! => permission denied"
        result = self.parser.parse(output, "1.1")
        self.assertFalse(result.success)

    def test_get_feedback_dict(self):
        """测试获取反馈字典。"""
        result = ExecutionResult(
            task_id="1.1",
            success=True,
            steps_executed=5,
            steps_failed=0,
            output=""
        )
        feedback = self.parser.get_feedback_dict(result)
        self.assertIn("success", feedback)
        self.assertIn("timestamp", feedback)


class TestErrorAnalyzer(unittest.TestCase):
    """ErrorAnalyzer 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.analyzer = ErrorAnalyzer()

    def test_classify_syntax_error(self):
        """测试分类语法错误。"""
        error_type = self.analyzer._classify_error("YAML syntax error")
        self.assertEqual(error_type, "syntax")

    def test_classify_connection_error(self):
        """测试分类连接错误。"""
        error_type = self.analyzer._classify_error("Connection failed")
        self.assertEqual(error_type, "connection")

    def test_classify_permission_error(self):
        """测试分类权限错误。"""
        error_type = self.analyzer._classify_error("Permission denied")
        self.assertEqual(error_type, "permission")

    def test_analyze_basic(self):
        """测试基础分析。"""
        analysis = self.analyzer.analyze("failed=2")
        self.assertIsInstance(analysis, ErrorAnalysis)
        self.assertIn(analysis.error_type, ["syntax", "connection", "permission", "command", "logic"])

    def test_get_common_cause(self):
        """测试获取常见原因。"""
        cause = self.analyzer._get_common_cause("syntax", "error")
        self.assertIn("YAML", cause)

    def test_get_suggestion(self):
        """测试获取建议。"""
        suggestion = self.analyzer._get_suggestion("connection")
        self.assertIsNotNone(suggestion)


class TestSelfHealer(unittest.TestCase):
    """SelfHealer 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.mock_llm = MagicMock()
        self.healer = SelfHealer(llm_client=self.mock_llm, max_retries=3)

    def test_can_retry(self):
        """测试是否可重试。"""
        self.assertTrue(self.healer.can_retry("syntax error"))
        self.assertFalse(self.healer.can_retry("invalid credentials"))

    def test_extract_yaml_from_code_block(self):
        """测试从代码块提取 YAML。"""
        text = """Here is the fixed playbook:
```yaml
- name: Test
  hosts: localhost
```
"""
        yaml = self.healer._extract_yaml(text)
        self.assertIn("- name: Test", yaml)

    def test_extract_yaml_plain(self):
        """测试提取纯 YAML。"""
        text = "- name: Test\n  hosts: localhost"
        yaml = self.healer._extract_yaml(text)
        self.assertIn("- name: Test", yaml)

    def test_extract_yaml_rejects_plain_explanation(self):
        """测试纯说明文字不会被当作 YAML 返回。"""
        text = "Here is the fixed playbook with some explanation only."
        yaml = self.healer._extract_yaml(text)
        self.assertEqual(yaml, "")

    def test_is_fixed(self):
        """测试判断是否已修复。"""
        analysis = ErrorAnalysis(
            error_type="syntax",
            error_message="error",
            root_cause="fixed",
            suggestion="The issue has been fixed",
            severity="high"
        )
        self.assertTrue(self.healer._is_fixed(analysis))

    def test_heal_no_llm(self):
        """测试无 LLM 时自愈。"""
        healer = SelfHealer(llm_client=None)
        result = healer.heal("playbook", "error")
        self.assertFalse(result.success)

    def test_rewrite_playbook_uses_error_log_in_prompt(self):
        """测试重写时会把错误日志注入 execution_log。"""
        self.mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- name: fixed\n  hosts: localhost\n```"""
        )

        _ = self.healer._rewrite_playbook(
            playbook="- name: old",
            failure_reason="syntax issue",
            execution_log="fatal: permission denied",
            original_rule="rule"
        )

        sent_prompt = self.mock_llm.generate.call_args.args[0]
        self.assertIn("fatal: permission denied", sent_prompt)

    def test_heal_stops_on_non_retryable_error(self):
        """不可重试错误应立即停止，不调用 LLM 重写。"""
        execute_fn = MagicMock()
        result = self.healer.heal(
            original_playbook="- hosts: localhost",
            error_log="authentication failed",
            original_rule="rule",
            execute_fn=execute_fn
        )
        self.assertFalse(result.success)
        self.assertEqual(self.mock_llm.generate.call_count, 0)
        self.assertEqual(result.attempts, 0)
        self.assertEqual(execute_fn.call_count, 0)

    def test_heal_returns_execution_result_on_success(self):
        """成功时应回传 execute_fn 的执行结果，供上层复用。"""
        self.mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- hosts: localhost\n  tasks: []\n```"""
        )
        retry_result = MagicMock(success=True, output="ok=1", error="")
        result = self.healer.heal(
            original_playbook="- hosts: localhost",
            error_log="fatal: something failed",
            original_rule="rule",
            execute_fn=lambda _: retry_result
        )
        self.assertTrue(result.success)
        self.assertIs(result.execution_result, retry_result)

    def test_heal_failed_attempt_count_matches_real_retries(self):
        """失败场景 attempts 应等于真实重写次数，而不是 max_retries 常量。"""
        self.mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- hosts: localhost\n  tasks: []\n```"""
        )

        failed_retry = MagicMock(success=False, output="", error="fatal: still failed")
        result = self.healer.heal(
            original_playbook="- hosts: localhost",
            error_log="fatal: first failed",
            original_rule="rule",
            execute_fn=lambda _: failed_retry
        )

        self.assertFalse(result.success)
        self.assertEqual(result.attempts, self.healer.max_retries)

    def test_get_healing_stats(self):
        """测试获取统计信息。"""
        results = [
            HealingResult(success=True, attempts=1),
            HealingResult(success=False, attempts=3)
        ]
        stats = self.healer.get_healing_stats(results)
        self.assertEqual(stats["total_attempts"], 2)
        self.assertEqual(stats["successful_healings"], 1)


if __name__ == "__main__":
    unittest.main()
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
