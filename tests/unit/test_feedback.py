"""单元测试 - Feedback 模块."""

from unittest.mock import MagicMock, patch
import pytest

from src.feedback.result_parser import ResultParser, ExecutionResult
from src.feedback.error_analyzer import ErrorAnalyzer, ErrorAnalysis
from src.feedback.self_heal import SelfHealer, HealingResult
from src.utils.yaml_utils import extract_yaml


class TestExecutionResult:
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
        assert result_dict["task_id"] == "1.1"
        assert result_dict["success"] is True


class TestResultParser:
    """ResultParser 测试类。"""

    @pytest.fixture
    def parser(self):
        """测试前准备。"""
        return ResultParser()

    def test_parse_success(self, parser):
        """测试解析成功结果。"""
        output = "ok=3 changed=2"
        result = parser.parse(output, "1.1")
        # _determine_success 检查 failed=和 unreachable=的出现次数
        # output 中没有这些字符串，所以 failed_count=0，success=True
        assert result.success is True
        assert result.steps_executed == 5  # ok=3 + changed=2

    def test_parse_success_with_zero_failure_fields(self, parser):
        """failed=0 和 unreachable=0 不应被视为失败。"""
        output = "ok=3 changed=2 failed=0 unreachable=0"
        result = parser.parse(output, "1.1")
        assert result.success is True
        assert result.steps_failed == 0
        assert result.steps_executed == 5

    def test_parse_failure(self, parser):
        """测试解析失败结果。"""
        output = "ok=3 failed=1 unreachable=1"
        result = parser.parse(output, "1.1")
        assert result.success is False
        assert result.steps_failed == 2

    def test_parse_failure_without_recap_but_with_failure_signal(self, parser):
        """无 recap 时，出现明确失败信号不能判定为成功。"""
        output = "fatal: [localhost]: FAILED! => permission denied"
        result = parser.parse(output, "1.1")
        assert result.success is False

    def test_get_feedback_dict(self, parser):
        """测试获取反馈字典。"""
        result = ExecutionResult(
            task_id="1.1",
            success=True,
            steps_executed=5,
            steps_failed=0,
            output=""
        )
        feedback = parser.get_feedback_dict(result)
        assert "success" in feedback
        assert "timestamp" in feedback


class TestErrorAnalyzer:
    """ErrorAnalyzer 测试类。"""

    @pytest.fixture
    def analyzer(self):
        """测试前准备。"""
        return ErrorAnalyzer()

    def test_classify_syntax_error(self, analyzer):
        """测试分类语法错误。"""
        error_type = analyzer._classify_error("YAML syntax error")
        assert error_type == "syntax"

    def test_classify_connection_error(self, analyzer):
        """测试分类连接错误。"""
        error_type = analyzer._classify_error("Connection failed")
        assert error_type == "connection"

    def test_classify_permission_error(self, analyzer):
        """测试分类权限错误。"""
        error_type = analyzer._classify_error("Permission denied")
        assert error_type == "permission"

    def test_analyze_basic(self, analyzer):
        """测试基础分析。"""
        analysis = analyzer.analyze("failed=2")
        assert isinstance(analysis, ErrorAnalysis)
        assert analysis.error_type in ["syntax", "connection", "permission", "command", "logic"]

    def test_get_common_cause(self, analyzer):
        """测试获取常见原因。"""
        cause = analyzer._get_common_cause("syntax", "error")
        assert "YAML" in cause

    def test_get_suggestion(self, analyzer):
        """测试获取建议。"""
        suggestion = analyzer._get_suggestion("connection")
        assert suggestion is not None


class TestSelfHealer:
    """SelfHealer 测试类。"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM 客户端。"""
        return MagicMock()

    @pytest.fixture
    def healer(self, mock_llm):
        """测试前准备。"""
        return SelfHealer(llm_client=mock_llm, max_retries=3)

    def test_can_retry(self, healer):
        """测试是否可重试。"""
        assert healer.can_retry("syntax error") is True
        assert healer.can_retry("invalid credentials") is False

    def test_extract_yaml_from_code_block(self, healer):
        """测试从代码块提取 YAML。"""
        text = """Here is the fixed playbook:
```yaml
- name: Test
  hosts: localhost
```
"""
        result = extract_yaml(text)
        assert result is not None
        assert "- name: Test" in result
        assert "```" not in result
        assert "Here is" not in result

    def test_extract_yaml_from_code_block_no_tag(self, healer):
        """测试从无 yaml 标签的代码块提取。"""
        text = """Result:
```
- name: NoTag
  hosts: localhost
  tasks: []
```
"""
        result = extract_yaml(text)
        assert result is not None
        assert "```" not in result
        assert "- name: NoTag" in result

    def test_extract_yaml_plain(self, healer):
        """测试提取纯 YAML。"""
        text = "- name: Test\n  hosts: localhost"
        result = extract_yaml(text)
        assert result is not None
        assert "- name: Test" in result

    def test_extract_yaml_with_dash_prefix(self, healer):
        """测试以 --- 开头的 YAML 提取。"""
        text = """---
- name: Play
  hosts: all
  tasks:
    - name: Do stuff
      command: echo ok
"""
        result = extract_yaml(text)
        assert result is not None
        assert "- name: Play" in result
        assert result.startswith("---")

    def test_extract_yaml_rejects_plain_explanation(self, healer):
        """测试纯说明文字不会被当作 YAML 返回。"""
        text = "Here is the fixed playbook with some explanation only."
        result = extract_yaml(text)
        assert result is None

    def test_is_fixed(self, healer):
        """测试判断是否已修复。"""
        analysis = ErrorAnalysis(
            error_type="syntax",
            error_message="error",
            root_cause="fixed",
            suggestion="The issue has been fixed",
            severity="high"
        )
        assert healer._is_fixed(analysis) is True

    def test_heal_no_llm(self):
        """测试无 LLM 时自愈。"""
        healer = SelfHealer(llm_client=None)
        result = healer.heal("playbook", "error")
        assert result.success is False

    def test_rewrite_playbook_uses_error_log_in_prompt(self, healer, mock_llm):
        """测试重写时会把错误日志注入 execution_log。"""
        mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- name: fixed\n  hosts: localhost\n```"""
        )

        _ = healer._rewrite_playbook(
            playbook="- name: old",
            failure_reason="syntax issue",
            execution_log="fatal: permission denied",
            original_rule="rule"
        )

        sent_prompt = mock_llm.generate.call_args.args[0]
        assert "fatal: permission denied" in sent_prompt

    def test_heal_stops_on_non_retryable_error(self, healer, mock_llm):
        """不可重试错误应立即停止，不调用 LLM 重写。"""
        execute_fn = MagicMock()
        result = healer.heal(
            original_playbook="- hosts: localhost",
            error_log="authentication failed",
            original_rule="rule",
            execute_fn=execute_fn
        )
        assert result.success is False
        assert mock_llm.generate.call_count == 0
        assert result.attempts == 0
        assert execute_fn.call_count == 0

    def test_heal_returns_execution_result_on_success(self, healer, mock_llm):
        """成功时应回传 execute_fn 的执行结果，供上层复用。"""
        mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- hosts: localhost\n  tasks: []\n```"""
        )
        retry_result = MagicMock(success=True, output="ok=1", error="")
        result = healer.heal(
            original_playbook="- hosts: localhost",
            error_log="fatal: something failed",
            original_rule="rule",
            execute_fn=lambda _: retry_result
        )
        assert result.success is True
        assert result.execution_result is retry_result

    def test_heal_failed_attempt_count_matches_real_retries(self, healer, mock_llm):
        """失败场景 attempts 应等于真实重写次数，而不是 max_retries 常量。"""
        mock_llm.generate.return_value = MagicMock(
            content="""```yaml\n- hosts: localhost\n  tasks: []\n```"""
        )

        failed_retry = MagicMock(success=False, output="", error="fatal: still failed")
        result = healer.heal(
            original_playbook="- hosts: localhost",
            error_log="fatal: first failed",
            original_rule="rule",
            execute_fn=lambda _: failed_retry
        )

        assert result.success is False
        assert result.attempts == healer.max_retries

    def test_get_healing_stats(self, healer):
        """测试获取统计信息。"""
        results = [
            HealingResult(success=True, attempts=1),
            HealingResult(success=False, attempts=3)
        ]
        stats = healer.get_healing_stats(results)
        assert stats["total_attempts"] == 2
        assert stats["successful_healings"] == 1

    # ── new tests for fix.md architecture requirements ────────────────────────

    def test_healing_result_has_failure_reason_field(self):
        """HealingResult must expose failure_reason field."""
        r = HealingResult(success=False, failure_reason="max retries exceeded")
        assert r.failure_reason == "max retries exceeded"

    def test_healing_result_failure_reason_default_empty(self):
        """failure_reason defaults to empty string."""
        r = HealingResult(success=True)
        assert r.failure_reason == ""

    def test_healing_result_has_backoff_delays_field(self):
        """HealingResult must expose backoff_delays list."""
        r = HealingResult(success=True, backoff_delays=[0.5, 1.0])
        assert r.backoff_delays == [0.5, 1.0]

    def test_healing_result_backoff_delays_default_empty(self):
        """backoff_delays defaults to empty list."""
        r = HealingResult(success=False)
        assert r.backoff_delays == []

    def test_heal_no_llm_sets_failure_reason(self):
        """heal() without LLM must set failure_reason."""
        healer = SelfHealer(llm_client=None)
        result = healer.heal("playbook", "error")
        assert result.failure_reason != ""

    def test_heal_max_retries_sets_failure_reason(self, healer, mock_llm):
        """After exhausting retries, failure_reason should be set."""
        mock_llm.generate.return_value = MagicMock(
            content="```yaml\n- hosts: localhost\n  tasks: []\n```"
        )
        failed = MagicMock(success=False, output="", error="fatal: still broken")
        result = healer.heal(
            "playbook", "fatal: first error", "rule",
            execute_fn=lambda _: failed
        )
        assert result.success is False
        assert result.failure_reason != ""
        assert "Max retries" in result.failure_reason or len(result.failure_reason) > 0

    def test_heal_backoff_delays_grow_with_retries(self, mock_llm):
        """Each retry after the first should have a longer delay than the previous."""
        import time
        healer = SelfHealer(llm_client=mock_llm, max_retries=3, backoff_base=0.001)
        mock_llm.generate.return_value = MagicMock(
            content="```yaml\n- hosts: localhost\n  tasks: []\n```"
        )
        failed = MagicMock(success=False, output="", error="fatal: err")
        result = healer.heal(
            "playbook", "fatal: err", "rule",
            execute_fn=lambda _: failed
        )
        # backoff_delays should have 2 entries (before attempt 2 and 3)
        assert len(result.backoff_delays) == 2
        assert result.backoff_delays[1] >= result.backoff_delays[0]

    def test_heal_drift_context_appended_to_prompt(self, healer, mock_llm):
        """When drift is provided, its JSON should appear in the LLM prompt."""
        mock_llm.generate.return_value = MagicMock(
            content="```yaml\n- hosts: localhost\n  tasks: []\n```"
        )
        # Create a minimal drift-like object with to_dict()
        drift_mock = MagicMock()
        drift_mock.to_dict.return_value = {
            "rule_id": "5.2.1",
            "is_compliant": False,
            "drifts": [{"key": "root_login", "expected": "no", "actual": "yes",
                        "comparison_type": "regex_match"}],
        }

        failed = MagicMock(success=False, output="", error="fatal: err")
        healer.heal(
            "playbook", "fatal: err", "rule",
            execute_fn=lambda _: failed,
            drift=drift_mock,
        )

        # Check at least one LLM call referenced the drift data
        assert mock_llm.generate.called
        prompt_used = mock_llm.generate.call_args.args[0]
        assert "5.2.1" in prompt_used or "drift" in prompt_used.lower()

    def test_heal_first_attempt_no_delay(self, mock_llm):
        """First attempt must not delay (backoff_delays length = retries - 1)."""
        healer = SelfHealer(llm_client=mock_llm, max_retries=2, backoff_base=0.001)
        mock_llm.generate.return_value = MagicMock(
            content="```yaml\n- hosts: localhost\n  tasks: []\n```"
        )
        failed = MagicMock(success=False, output="", error="fatal: err")
        result = healer.heal(
            "playbook", "fatal: err", "rule",
            execute_fn=lambda _: failed
        )
        # max_retries=2 means 2 attempts → 1 backoff (before attempt 2)
        assert len(result.backoff_delays) == 1
