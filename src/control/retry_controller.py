"""Retry Controller - Implements controlled self-healing logic.

Manages retry attempts with structured error capture, failure tracking,
and convergence guarantees.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class FailureType(Enum):
    """Categorized failure types for structured error handling."""
    SYNTAX_ERROR = "syntax_error"
    PERMISSION_ERROR = "permission_error"
    DEPENDENCY_ERROR = "dependency_error"
    TIMEOUT_ERROR = "timeout_error"
    VERIFICATION_ERROR = "verification_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class FailureRecord:
    """Structured failure record for tracking and analysis."""
    timestamp: datetime
    failure_type: FailureType
    error_message: str
    rule_id: str
    attempt_number: int
    remediation_command: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "rule_id": self.rule_id,
            "attempt_number": self.attempt_number,
            "remediation_command": self.remediation_command,
            "metadata": self.metadata
        }


class RetryController:
    """Controlled retry logic with convergence guarantees.

    Implements structured error capture, failure tracking, and stop conditions
    to ensure system stability and reproducibility.
    """

    def __init__(self, max_retry_count: int = 3):
        self.max_retry_count = max_retry_count
        self.failure_history: List[FailureRecord] = []
        self.rule_attempts: Dict[str, int] = {}
        self.convergence_threshold = 0  # Minimum improvement required

    def should_retry(self, rule_id: str, current_drift_count: int,
                    previous_drift_count: Optional[int] = None) -> bool:
        """Determine if retry should be attempted based on convergence logic.

        Args:
            rule_id: The rule being processed
            current_drift_count: Current number of drifts
            previous_drift_count: Drift count from previous attempt

        Returns:
            True if retry should be attempted
        """
        current_attempts = self.rule_attempts.get(rule_id, 0)

        # Check max retry limit
        if current_attempts >= self.max_retry_count:
            return False

        # Check convergence: only after first attempt
        if current_attempts > 0 and previous_drift_count is not None:
            improvement = previous_drift_count - current_drift_count
            if improvement <= self.convergence_threshold and current_drift_count > 0:
                return False

        return True

    def record_failure(self, rule_id: str, error_message: str,
                      failure_type: FailureType = FailureType.UNKNOWN_ERROR,
                      remediation_command: str = "",
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a failure for analysis and future retry decisions."""
        attempt_number = self.rule_attempts.get(rule_id, 0) + 1

        failure = FailureRecord(
            timestamp=datetime.now(),
            failure_type=failure_type,
            error_message=error_message,
            rule_id=rule_id,
            attempt_number=attempt_number,
            remediation_command=remediation_command,
            metadata=metadata or {}
        )

        self.failure_history.append(failure)
        self.rule_attempts[rule_id] = attempt_number

    def categorize_error(self, error_message: str) -> FailureType:
        """Categorize error message into failure types."""
        msg_lower = error_message.lower()

        if "syntax" in msg_lower or "parse" in msg_lower:
            return FailureType.SYNTAX_ERROR
        elif "permission" in msg_lower or "access denied" in msg_lower:
            return FailureType.PERMISSION_ERROR
        elif "dependency" in msg_lower or "not found" in msg_lower:
            return FailureType.DEPENDENCY_ERROR
        elif "timeout" in msg_lower:
            return FailureType.TIMEOUT_ERROR
        elif "verification" in msg_lower or "drift" in msg_lower:
            return FailureType.VERIFICATION_ERROR
        else:
            return FailureType.UNKNOWN_ERROR

    def get_failure_pattern(self, rule_id: str) -> Dict[str, Any]:
        """Analyze failure patterns for a rule to inform retry strategy."""
        rule_failures = [f for f in self.failure_history if f.rule_id == rule_id]

        if not rule_failures:
            return {}

        failure_types = {}
        for failure in rule_failures:
            ft = failure.failure_type.value
            failure_types[ft] = failure_types.get(ft, 0) + 1

        most_common_failure = max(failure_types, key=failure_types.get)

        return {
            "total_failures": len(rule_failures),
            "most_common_failure": most_common_failure,
            "attempts": len(rule_failures),
            "failure_distribution": failure_types
        }

    def reset_rule(self, rule_id: str) -> None:
        """Reset retry state for a specific rule."""
        if rule_id in self.rule_attempts:
            del self.rule_attempts[rule_id]

    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get overall retry statistics for analysis."""
        total_attempts = sum(self.rule_attempts.values())
        rules_attempted = len(self.rule_attempts)
        avg_attempts = total_attempts / rules_attempted if rules_attempted > 0 else 0

        return {
            "total_attempts": total_attempts,
            "rules_attempted": rules_attempted,
            "average_attempts_per_rule": avg_attempts,
            "max_retry_limit": self.max_retry_count
        }