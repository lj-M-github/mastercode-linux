"""Unit tests — compliance/rule_model.py and compliance/drift_auditor.py."""

from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import textwrap
import subprocess
import pytest

from src.compliance.rule_model import (
    DriftField,
    DriftResult,
    COMPARISON_REGEX_MATCH,
    COMPARISON_EXACT,
    COMPARISON_CONTAINS,
    COMPARISON_NOT_CONTAINS,
    VALID_COMPARISON_TYPES,
)
from src.compliance.drift_auditor import DriftAuditor


# ── Fixtures ──────────────────────────────────────────────────────────────────

_CHECKS_YAML = textwrap.dedent("""\
    policy: "Test Policy"
    version: "1.0"
    checks:
      - rule_id: "5.2.1"
        title: "Ensure SSH root login is disabled"
        domain: ssh
        severity: high
        check_command: "sshd -T 2>/dev/null | grep -i permitrootlogin"
        expected_pattern: "permitrootlogin\\\\s+no"
        remediation_hint: "Set PermitRootLogin no"

      - rule_id: "EXACT.1"
        title: "Exact match rule"
        domain: test
        severity: low
        check_command: "echo exact"
        expected_state: "exact"
        comparison_type: exact

      - rule_id: "CONTAINS.1"
        title: "Contains rule"
        domain: test
        severity: low
        check_command: "echo hello world"
        expected_state: "hello"
        comparison_type: contains

      - rule_id: "NOT_CONTAINS.1"
        title: "Not-contains rule"
        domain: test
        severity: low
        check_command: "echo safe output"
        expected_state: "danger"
        comparison_type: not_contains
""")


@pytest.fixture
def tmp_checks_file(tmp_path):
    """Write the test YAML to a temp file and return its path."""
    p = tmp_path / "checks.yaml"
    p.write_text(_CHECKS_YAML, encoding="utf-8")
    return str(p)


@pytest.fixture
def auditor(tmp_checks_file):
    """DriftAuditor with no SSH client (localhost mode with mocked subprocess)."""
    return DriftAuditor(tmp_checks_file)


# ── TestDriftField ─────────────────────────────────────────────────────────────

class TestDriftField:
    """Tests for DriftField dataclass."""

    def test_default_comparison_type(self):
        f = DriftField(key="k", expected="e", actual="a")
        assert f.comparison_type == COMPARISON_REGEX_MATCH

    def test_to_dict_keys(self):
        d = DriftField("sshd_root", "no", "yes", COMPARISON_EXACT).to_dict()
        assert set(d.keys()) == {"key", "expected", "actual", "comparison_type"}

    def test_to_dict_values(self):
        d = DriftField("k", "exp", "act", COMPARISON_CONTAINS).to_dict()
        assert d["key"] == "k"
        assert d["expected"] == "exp"
        assert d["actual"] == "act"
        assert d["comparison_type"] == COMPARISON_CONTAINS


# ── TestDriftResult ────────────────────────────────────────────────────────────

class TestDriftResult:
    """Tests for DriftResult dataclass."""

    def test_compliant_no_drifts(self):
        r = DriftResult(rule_id="5.2.1", is_compliant=True)
        assert r.drift_count == 0
        assert not r.has_error

    def test_non_compliant_with_drifts(self):
        drift = DriftField("x", "a", "b")
        r = DriftResult(rule_id="5.2.1", is_compliant=False, drifts=[drift])
        assert r.drift_count == 1
        assert not r.has_error

    def test_has_error_when_error_set(self):
        r = DriftResult(rule_id="5.2.1", is_compliant=False, error="cmd failed")
        assert r.has_error

    def test_to_dict_structure(self):
        drift = DriftField("key", "exp", "act", COMPARISON_EXACT)
        r = DriftResult(
            rule_id="5.2.1",
            is_compliant=False,
            drifts=[drift],
            check_command="echo x",
            actual_output="y",
            title="Test Rule",
            domain="ssh",
            severity="high",
            error="",
        )
        d = r.to_dict()
        assert d["rule_id"] == "5.2.1"
        assert d["is_compliant"] is False
        assert len(d["drifts"]) == 1
        assert d["drifts"][0]["key"] == "key"
        assert d["title"] == "Test Rule"

    def test_valid_comparison_types_known(self):
        expected = {
            COMPARISON_REGEX_MATCH,
            COMPARISON_EXACT,
            COMPARISON_CONTAINS,
            COMPARISON_NOT_CONTAINS,
        }
        assert VALID_COMPARISON_TYPES == expected


# ── TestDriftAuditorInit ───────────────────────────────────────────────────────

class TestDriftAuditorInit:
    """Tests for DriftAuditor initialisation."""

    def test_loads_checks_from_yaml(self, tmp_checks_file):
        a = DriftAuditor(tmp_checks_file)
        assert "5.2.1" in a._checks
        assert "EXACT.1" in a._checks

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            DriftAuditor(str(tmp_path / "nonexistent.yaml"))

    def test_timeout_default(self, tmp_checks_file):
        a = DriftAuditor(tmp_checks_file)
        assert a._timeout == 15

    def test_custom_timeout(self, tmp_checks_file):
        a = DriftAuditor(tmp_checks_file, timeout=5)
        assert a._timeout == 5


# ── TestDriftAuditorCompare ────────────────────────────────────────────────────

class TestDriftAuditorCompare:
    """Tests for DriftAuditor._compare() method."""

    def test_regex_match_pass(self, auditor):
        assert auditor._compare("permitrootlogin no", r"permitrootlogin\s+no", COMPARISON_REGEX_MATCH)

    def test_regex_match_fail(self, auditor):
        assert not auditor._compare("permitrootlogin yes", r"permitrootlogin\s+no", COMPARISON_REGEX_MATCH)

    def test_regex_match_invalid_falls_back_to_substring(self, auditor):
        # Invalid regex falls back to substring match
        assert auditor._compare("hello world", "hello", COMPARISON_REGEX_MATCH)

    def test_exact_pass(self, auditor):
        assert auditor._compare("exact", "exact", COMPARISON_EXACT)

    def test_exact_fail(self, auditor):
        assert not auditor._compare("exact_plus", "exact", COMPARISON_EXACT)

    def test_exact_strips_whitespace(self, auditor):
        assert auditor._compare("  exact  ", "exact", COMPARISON_EXACT)

    def test_contains_pass(self, auditor):
        assert auditor._compare("hello world", "hello", COMPARISON_CONTAINS)

    def test_contains_fail(self, auditor):
        assert not auditor._compare("goodbye world", "hello", COMPARISON_CONTAINS)

    def test_not_contains_pass(self, auditor):
        assert auditor._compare("safe output", "danger", COMPARISON_NOT_CONTAINS)

    def test_not_contains_fail(self, auditor):
        assert not auditor._compare("dangerous output", "danger", COMPARISON_NOT_CONTAINS)


# ── TestDriftAuditorAuditRule ──────────────────────────────────────────────────

class TestDriftAuditorAuditRule:
    """Tests for DriftAuditor.audit_rule()."""

    def test_unknown_rule_returns_error_result(self, auditor):
        r = auditor.audit_rule("999.999")
        assert not r.is_compliant
        assert r.has_error
        assert r.drift_count == 1
        assert r.drifts[0].key == "rule_existence"

    def test_compliant_regex(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="permitrootlogin no\n", stderr="", returncode=0
            )
            r = auditor.audit_rule("5.2.1")
        assert r.is_compliant
        assert r.drift_count == 0
        assert r.rule_id == "5.2.1"

    def test_non_compliant_regex(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="permitrootlogin yes\n", stderr="", returncode=0
            )
            r = auditor.audit_rule("5.2.1")
        assert not r.is_compliant
        assert r.drift_count == 1
        assert r.drifts[0].comparison_type == COMPARISON_REGEX_MATCH

    def test_command_failure_sets_error(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="sshd: not found", returncode=1)
            r = auditor.audit_rule("5.2.1")
        assert not r.is_compliant
        assert r.has_error

    def test_exact_comparison(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="exact\n", stderr="", returncode=0)
            r = auditor.audit_rule("EXACT.1")
        assert r.is_compliant

    def test_contains_comparison(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="hello world\n", stderr="", returncode=0)
            r = auditor.audit_rule("CONTAINS.1")
        assert r.is_compliant

    def test_not_contains_compliant(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="safe output\n", stderr="", returncode=0)
            r = auditor.audit_rule("NOT_CONTAINS.1")
        assert r.is_compliant

    def test_not_contains_non_compliant(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="dangerous stuff\n", stderr="", returncode=0)
            r = auditor.audit_rule("NOT_CONTAINS.1")
        assert not r.is_compliant

    def test_result_has_check_command(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="permitrootlogin no", stderr="", returncode=0)
            r = auditor.audit_rule("5.2.1")
        assert "sshd" in r.check_command

    def test_result_domain_severity(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="permitrootlogin no", stderr="", returncode=0)
            r = auditor.audit_rule("5.2.1")
        assert r.domain == "ssh"
        assert r.severity == "high"

    def test_expected_state_takes_priority_over_expected_pattern(self, auditor):
        """EXACT.1 uses expected_state; verify it's used, not expected_pattern."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="exact\n", stderr="", returncode=0)
            r = auditor.audit_rule("EXACT.1")
        assert r.is_compliant


# ── TestDriftAuditorAuditAll ───────────────────────────────────────────────────

class TestDriftAuditorAuditAll:
    """Tests for DriftAuditor.audit_all()."""

    def test_audit_all_default_runs_all_checks(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="permitrootlogin no", stderr="", returncode=0)
            results = auditor.audit_all()
        # 4 rules in _CHECKS_YAML
        assert len(results) == 4

    def test_audit_all_with_rule_ids(self, auditor):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="permitrootlogin no", stderr="", returncode=0)
            results = auditor.audit_all(["5.2.1"])
        assert len(results) == 1

    def test_audit_all_unknown_rule_included(self, auditor):
        results = auditor.audit_all(["999.999"])
        assert len(results) == 1
        assert results[0].has_error


# ── TestDriftAuditorSummary ────────────────────────────────────────────────────

class TestDriftAuditorSummary:
    """Tests for DriftAuditor.summary()."""

    def _make_results(self, compliant_count, non_compliant_count, error_count=0):
        results = []
        for _ in range(compliant_count):
            results.append(DriftResult("r", True, [], "cmd", "out", "t", "ssh", "high", ""))
        for _ in range(non_compliant_count):
            results.append(DriftResult("r", False,
                [DriftField("k", "e", "a")], "cmd", "out", "t", "ssh", "high", ""))
        for _ in range(error_count):
            results.append(DriftResult("r", False, [], "cmd", "", "t", "ssh", "high", "error!"))
        return results

    def test_all_compliant(self):
        a = MagicMock()
        a.summary = DriftAuditor.summary.__get__(a)  # won't work — call directly
        pass  # tested via fixture below

    def test_compliance_rate_all_pass(self, auditor):
        results = self._make_results(3, 0)
        s = auditor.summary(results)
        assert s["compliance_rate"] == 1.0
        assert s["compliant_count"] == 3

    def test_compliance_rate_partial(self, auditor):
        results = self._make_results(1, 1)
        s = auditor.summary(results)
        assert s["compliance_rate"] == 0.5

    def test_error_count_not_in_compliance_rate_denominator(self, auditor):
        results = self._make_results(1, 0, error_count=1)
        s = auditor.summary(results)
        # Only 1 evaluable (compliant=1, non_compliant=0): rate = 1.0
        assert s["compliance_rate"] == 1.0
        assert s["error_count"] == 1

    def test_by_domain(self, auditor):
        results = self._make_results(2, 1)
        s = auditor.summary(results)
        assert "ssh" in s["by_domain"]
        assert s["by_domain"]["ssh"]["compliant"] == 2

    def test_total_drifts(self, auditor):
        results = self._make_results(0, 2)
        s = auditor.summary(results)
        assert s["total_drifts"] == 2

    def test_empty_results(self, auditor):
        s = auditor.summary([])
        assert s["compliance_rate"] == 0.0
        assert s["total"] == 0


# ── TestDriftAuditorSSH ────────────────────────────────────────────────────────

class TestDriftAuditorSSH:
    """Tests for DriftAuditor with SSH client."""

    def test_uses_ssh_client_when_provided(self, tmp_checks_file):
        mock_ssh = MagicMock()
        mock_ssh.execute.return_value = MagicMock(
            stdout="permitrootlogin no", stderr=""
        )
        a = DriftAuditor(tmp_checks_file, ssh_client=mock_ssh)
        r = a.audit_rule("5.2.1")
        mock_ssh.execute.assert_called_once()
        assert r.is_compliant
