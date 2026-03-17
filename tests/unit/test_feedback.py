"""单元测试 - Feedback 模块."""

from unittest.mock import MagicMock, patch
import pytest

from src.feedback.result_parser import ResultParser, ExecutionResult
from src.feedback.error_analyzer import ErrorAnalyzer, ErrorAnalysis
from src.feedback.self_heal import SelfHealer, HealingResult


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
        yaml = healer._extract_yaml(text)
        assert "- name: Test" in yaml

    def test_extract_yaml_plain(self, healer):
        """测试提取纯 YAML。"""
        text = "- name: Test\n  hosts: localhost"
        yaml = healer._extract_yaml(text)
        assert "- name: Test" in yaml

    def test_extract_yaml_rejects_plain_explanation(self, healer):
        """测试纯说明文字不会被当作 YAML 返回。"""
        text = "Here is the fixed playbook with some explanation only."
        yaml = healer._extract_yaml(text)
        assert yaml == ""

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
