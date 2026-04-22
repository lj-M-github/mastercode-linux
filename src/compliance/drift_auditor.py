"""Drift Auditor — Deterministic, rule-driven compliance audit engine.

Design contract (from fix.md):
  • Audit MUST NOT depend on LLM output.
  • Compliance rules are structured rule models: {rule_id, check_command,
    expected_state, comparison_type}.
  • Audit executes check_command, parses output deterministically, performs
    structured state comparison, and produces DriftResult objects.
  • No LLM involvement in audit phase.

Comparison types:
  regex_match   — re.search(expected, actual)   (default; backward-compatible)
  exact         — actual.strip() == expected.strip()
  contains      — expected substring is present in actual
  not_contains  — expected substring is absent from actual
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from .rule_model import (
    DriftField,
    DriftResult,
    COMPARISON_REGEX_MATCH,
    COMPARISON_EXACT,
    COMPARISON_CONTAINS,
    COMPARISON_NOT_CONTAINS,
    COMPARISON_NUMERIC,
    COMPARISON_BOOLEAN,
)

_DEFAULT_COMPARISON = COMPARISON_REGEX_MATCH


class DriftAuditor:
    """Deterministic drift auditor.

    Loads compliance check specifications from a YAML file, executes each
    check_command on the target host (localhost or via SSH), and returns
    structured DriftResult objects that describe *what* drifted and *how*.

    YAML spec format (backward compatible with existing cis_rhel9_checks.yaml):

        checks:
          - rule_id: "5.2.1"
            title: "Ensure SSH root login is disabled"
            domain: ssh
            severity: high
            check_command: "sshd -T 2>/dev/null | grep -i permitrootlogin"
            expected_pattern: "permitrootlogin\\s+no"   # legacy field
            # optional new fields:
            expected_state: "permitrootlogin\\s+no"      # takes priority
            comparison_type: regex_match                  # default
            remediation_hint: "Set PermitRootLogin no in /etc/ssh/sshd_config"

    Attributes:
        checks_file: Path to compliance check YAML specification.
        ssh_client:  SSHClient instance; None means localhost subprocess mode.
        _checks:     Dict[rule_id, check_spec] loaded from YAML.
        _timeout:    Per-command timeout in seconds.

    Examples:
        >>> auditor = DriftAuditor("data/compliance_checks/cis_rhel9_checks.yaml")
        >>> result = auditor.audit_rule("5.2.1")
        >>> print(result.is_compliant, result.drifts)

        >>> # SSH mode
        >>> from src.executor.ssh_client import SSHClient, SSHConfig
        >>> client = SSHClient(SSHConfig(host="10.0.0.5", username="ec2-user"))
        >>> auditor = DriftAuditor("checks.yaml", ssh_client=client)
        >>> results = auditor.audit_all(["5.2.1", "6.1.1"])
    """

    def __init__(
        self,
        checks_file: str,
        ssh_client=None,
        timeout: int = 15,
    ):
        self.checks_file = Path(checks_file)
        self.ssh_client = ssh_client
        self._timeout = timeout
        self._checks: Dict[str, Dict[str, Any]] = {}
        self._load_checks()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _load_checks(self) -> None:
        """Load and index compliance check specs from YAML."""
        if not self.checks_file.exists():
            raise FileNotFoundError(
                f"Compliance checks file not found: {self.checks_file}"
            )
        raw = self.checks_file.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        for check in data.get("checks", []):
            rule_id = check.get("rule_id", "")
            if rule_id:
                self._checks[rule_id] = check

    def _run_command_local(self, command: str) -> tuple[str, str]:
        """Execute shell command on localhost via subprocess."""
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            return proc.stdout.strip(), proc.stderr.strip()
        except subprocess.TimeoutExpired:
            return "", f"Command timed out after {self._timeout}s"
        except Exception as exc:
            return "", str(exc)

    def _run_command_ssh(self, command: str) -> tuple[str, str]:
        """Execute shell command on a remote host via SSH with sudo."""
        result = self.ssh_client.execute(f"sudo {command}", timeout=self._timeout)
        return result.stdout.strip(), result.stderr.strip()

    def _run_command(self, command: str) -> tuple[str, str]:
        """Execute command using SSH or localhost, depending on configuration."""
        if self.ssh_client is not None:
            return self._run_command_ssh(command)
        return self._run_command_local(command)

    def _compare(self, actual: str, expected: str, comparison_type: str) -> bool:
        """Compare actual output against expected value using the specified method.

        Args:
            actual:          Command stdout.
            expected:        Expected state expression.
            comparison_type: One of the COMPARISON_* constants.

        Returns:
            True if the system state matches the expected state.
        """
        if comparison_type == COMPARISON_EXACT:
            return actual.strip() == expected.strip()
        if comparison_type == COMPARISON_CONTAINS:
            return expected.lower() in actual.lower()
        if comparison_type == COMPARISON_NOT_CONTAINS:
            return expected.lower() not in actual.lower()
        if comparison_type == COMPARISON_NUMERIC:
            try:
                return float(actual.strip()) == float(expected.strip())
            except ValueError:
                return False
        if comparison_type == COMPARISON_BOOLEAN:
            actual_bool = actual.strip().lower() in ('true', '1', 'yes', 'on')
            expected_bool = expected.strip().lower() in ('true', '1', 'yes', 'on')
            return actual_bool == expected_bool
        # Default: regex_match
        try:
            return bool(re.search(expected, actual, re.IGNORECASE | re.MULTILINE))
        except re.error:
            # Regex is malformed — fall back to substring match
            return expected.lower() in actual.lower()

    # ── Public interface ─────────────────────────────────────────────────────

    def audit_rule(self, rule_id: str) -> DriftResult:
        """Execute a single compliance check and return a structured DriftResult.

        Args:
            rule_id: CIS or policy rule identifier (e.g. "5.2.1").

        Returns:
            DriftResult — is_compliant=True means no drift; otherwise drifts
            list contains explicit field-level discrepancies.
        """
        check = self._checks.get(rule_id)
        if check is None:
            return DriftResult(
                rule_id=rule_id,
                is_compliant=False,
                drifts=[
                    DriftField(
                        key="rule_existence",
                        expected="rule specification exists",
                        actual="no check specification found",
                        comparison_type=COMPARISON_EXACT,
                    )
                ],
                error=f"No check specification found for rule_id={rule_id!r}",
            )

        cmd = check["check_command"]
        # Accept either new `expected_state` or legacy `expected_pattern`
        expected = check.get("expected_state") or check.get("expected_pattern", "")
        comparison_type = check.get("comparison_type", _DEFAULT_COMPARISON)

        stdout, stderr = self._run_command(cmd)

        # Command execution failure → cannot determine compliance
        if stderr and not stdout:
            return DriftResult(
                rule_id=rule_id,
                is_compliant=False,
                drifts=[
                    DriftField(
                        key="command_execution",
                        expected="command executes without error",
                        actual=f"stderr: {stderr}",
                        comparison_type=COMPARISON_EXACT,
                    )
                ],
                check_command=cmd,
                actual_output="",
                title=check.get("title", ""),
                domain=check.get("domain", ""),
                severity=check.get("severity", ""),
                error=stderr,
            )

        matched = self._compare(stdout, expected, comparison_type)

        drifts: List[DriftField] = []
        if not matched:
            drifts.append(
                DriftField(
                    key=check.get("title", rule_id),
                    expected=expected,
                    actual=stdout,
                    comparison_type=comparison_type,
                )
            )

        return DriftResult(
            rule_id=rule_id,
            is_compliant=matched,
            drifts=drifts,
            check_command=cmd,
            actual_output=stdout,
            title=check.get("title", ""),
            domain=check.get("domain", ""),
            severity=check.get("severity", ""),
            error="",
        )

    def audit_all(
        self,
        rule_ids: Optional[List[str]] = None,
    ) -> List[DriftResult]:
        """Execute compliance checks for all (or selected) rules.

        Args:
            rule_ids: Specific rule IDs to audit; None audits all loaded rules.

        Returns:
            List of DriftResult in same order as rule_ids.
        """
        targets = rule_ids if rule_ids is not None else list(self._checks.keys())
        return [self.audit_rule(rid) for rid in targets]

    def summary(
        self,
        results: Optional[List[DriftResult]] = None,
    ) -> Dict[str, Any]:
        """Aggregate DriftResult statistics.

        Args:
            results: Pre-computed results; None triggers audit_all().

        Returns:
            Dict with compliant_count, non_compliant_count, error_count,
            total_drifts, compliance_rate, by_domain, by_severity.
        """
        if results is None:
            results = self.audit_all()

        compliant_count = sum(1 for r in results if r.is_compliant)
        error_count = sum(1 for r in results if r.has_error)
        non_compliant_count = len(results) - compliant_count - error_count
        if non_compliant_count < 0:
            non_compliant_count = 0
        total_drifts = sum(r.drift_count for r in results)

        evaluable = compliant_count + non_compliant_count
        compliance_rate = compliant_count / evaluable if evaluable > 0 else 0.0

        by_domain: Dict[str, Dict[str, int]] = {}
        for r in results:
            domain = r.domain or "unknown"
            stats = by_domain.setdefault(
                domain, {"compliant": 0, "non_compliant": 0, "error": 0}
            )
            if r.is_compliant:
                stats["compliant"] += 1
            elif r.has_error:
                stats["error"] += 1
            else:
                stats["non_compliant"] += 1

        by_severity: Dict[str, Dict[str, int]] = {}
        for r in results:
            sev = r.severity or "unknown"
            stats = by_severity.setdefault(sev, {"compliant": 0, "non_compliant": 0})
            if r.is_compliant:
                stats["compliant"] += 1
            else:
                stats["non_compliant"] += 1

        return {
            "total": len(results),
            "compliant_count": compliant_count,
            "non_compliant_count": non_compliant_count,
            "error_count": error_count,
            "total_drifts": total_drifts,
            "compliance_rate": compliance_rate,
            "by_domain": by_domain,
            "by_severity": by_severity,
        }
