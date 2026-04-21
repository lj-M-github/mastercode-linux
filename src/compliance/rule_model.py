"""Rule Models - Structured data models for deterministic compliance audit.

Defines:
  DriftField  — a single field discrepancy between expected and actual state
  DriftResult — full structured audit result for one rule
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

# Supported comparison types for DriftField / DriftAuditor
COMPARISON_REGEX_MATCH = "regex_match"
COMPARISON_EXACT = "exact"
COMPARISON_CONTAINS = "contains"
COMPARISON_NOT_CONTAINS = "not_contains"
COMPARISON_NUMERIC = "numeric"
COMPARISON_BOOLEAN = "boolean"

VALID_COMPARISON_TYPES = {
    COMPARISON_REGEX_MATCH,
    COMPARISON_EXACT,
    COMPARISON_CONTAINS,
    COMPARISON_NOT_CONTAINS,
    COMPARISON_NUMERIC,
    COMPARISON_BOOLEAN,
}


@dataclass
class DriftField:
    """A single field drift between expected and actual configuration state.

    Attributes:
        key:             Human-readable name of the checked field / policy item.
        expected:        Expected state (pattern, value, or expression).
        actual:          Actual observed state from the system.
        comparison_type: Method used to compare expected vs actual.
                         One of "regex_match" | "exact" | "contains" | "not_contains" | "numeric" | "boolean".
    """

    key: str
    expected: str
    actual: str
    comparison_type: str = COMPARISON_REGEX_MATCH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "expected": self.expected,
            "actual": self.actual,
            "comparison_type": self.comparison_type,
        }


@dataclass
class DriftResult:
    """Structured compliance drift result for a single rule.

    Replaces boolean pass/fail with explicit drift representation.

    Attributes:
        rule_id:      CIS rule identifier (e.g., "5.2.1")
        is_compliant: Boolean indicating overall compliance status
        drifts:       List of specific drift fields (empty if compliant)
        title:        Rule title for context
        domain:       Security domain (ssh/filesystem/kernel/audit/firewall)
        severity:     Rule severity (high/medium/low)
        check_command: The command executed for auditing
        actual_output: Raw output from check command
        error:        Execution error message (if any)
    """
    rule_id: str
    is_compliant: bool
    drifts: List[DriftField] = field(default_factory=list)
    title: str = ""
    domain: str = ""
    severity: str = ""
    check_command: str = ""
    actual_output: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "is_compliant": self.is_compliant,
            "drifts": [drift.to_dict() for drift in self.drifts],
            "title": self.title,
            "domain": self.domain,
            "severity": self.severity,
            "check_command": self.check_command,
            "actual_output": self.actual_output,
            "error": self.error,
        }


@dataclass
class DriftResult:
    """Structured compliance audit result for a single rule.

    Attributes:
        rule_id:        CIS or policy rule identifier (e.g. "5.2.1").
        is_compliant:   True if actual state matches expected state; False otherwise.
        drifts:         List of explicit field-level discrepancies.
                        Empty when is_compliant is True.
        check_command:  Shell command that was executed to determine state.
        actual_output:  Raw stdout produced by check_command.
        title:          Human-readable rule title.
        domain:         Security domain (e.g. "ssh", "filesystem", "kernel").
        severity:       Rule severity — "high" | "medium" | "low".
        error:          Non-empty when the check could not be executed (skip state).
    """

    rule_id: str
    is_compliant: bool
    drifts: List[DriftField] = field(default_factory=list)
    check_command: str = ""
    actual_output: str = ""
    title: str = ""
    domain: str = ""
    severity: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "is_compliant": self.is_compliant,
            "drifts": [d.to_dict() for d in self.drifts],
            "check_command": self.check_command,
            "actual_output": self.actual_output,
            "title": self.title,
            "domain": self.domain,
            "severity": self.severity,
            "error": self.error,
        }

    @property
    def has_error(self) -> bool:
        """True when the check could not be run (command execution failure)."""
        return bool(self.error)

    @property
    def drift_count(self) -> int:
        """Number of detected drift fields."""
        return len(self.drifts)
