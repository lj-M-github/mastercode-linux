"""State Manager - Implements compliance state machine model.

Defines the formal state transition model for compliance remediation workflow.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


class ComplianceState(Enum):
    """Compliance state machine states."""
    COMPLIANT = "compliant"
    DRIFT_DETECTED = "drift_detected"
    REMEDIATION_GENERATED = "remediation_generated"
    EXECUTION_FAILED = "execution_failed"
    VERIFICATION_FAILED = "verification_failed"
    REMEDIATION_SUCCEEDED = "remediation_succeeded"
    UNRESOLVED = "unresolved"


@dataclass
class StateTransition:
    """Represents a state transition with metadata."""
    from_state: ComplianceState
    to_state: ComplianceState
    timestamp: datetime
    reason: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StateManager:
    """Manages compliance state machine transitions and history.

    Implements the formal state transition model with convergence guarantees.
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        ComplianceState.COMPLIANT: [ComplianceState.DRIFT_DETECTED],
        ComplianceState.DRIFT_DETECTED: [ComplianceState.REMEDIATION_GENERATED],
        ComplianceState.REMEDIATION_GENERATED: [
            ComplianceState.EXECUTION_FAILED,
            ComplianceState.VERIFICATION_FAILED,
            ComplianceState.REMEDIATION_SUCCEEDED
        ],
        ComplianceState.EXECUTION_FAILED: [
            ComplianceState.REMEDIATION_GENERATED,
            ComplianceState.UNRESOLVED
        ],
        ComplianceState.VERIFICATION_FAILED: [
            ComplianceState.REMEDIATION_GENERATED,
            ComplianceState.UNRESOLVED
        ],
        ComplianceState.REMEDIATION_SUCCEEDED: [ComplianceState.COMPLIANT],
        ComplianceState.UNRESOLVED: []  # Terminal state
    }

    def __init__(self, max_retries: int = 3):
        self.current_state = ComplianceState.COMPLIANT
        self.max_retries = max_retries
        self.retry_count = 0
        self.transition_history: List[StateTransition] = []
        self.rule_states: Dict[str, ComplianceState] = {}

    def get_current_state(self, rule_id: Optional[str] = None) -> ComplianceState:
        """Get current state for a specific rule or global state."""
        if rule_id:
            return self.rule_states.get(rule_id, ComplianceState.COMPLIANT)
        return self.current_state

    def can_transition(self, to_state: ComplianceState,
                      rule_id: Optional[str] = None) -> bool:
        """Check if transition to target state is valid."""
        from_state = self.get_current_state(rule_id)
        return to_state in self.VALID_TRANSITIONS[from_state]

    def transition(self, to_state: ComplianceState, reason: str,
                  rule_id: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Attempt state transition with validation."""
        from_state = self.get_current_state(rule_id)

        if not self.can_transition(to_state, rule_id):
            return False

        # Check retry limits for retry transitions
        if to_state in [ComplianceState.REMEDIATION_GENERATED]:
            if self.retry_count >= self.max_retries:
                # Force transition to UNRESOLVED
                to_state = ComplianceState.UNRESOLVED
                reason = f"Max retries ({self.max_retries}) exceeded"

        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.now(),
            reason=reason,
            metadata=metadata or {}
        )

        self.transition_history.append(transition)

        if rule_id:
            self.rule_states[rule_id] = to_state
        else:
            self.current_state = to_state

        # Update retry count
        if to_state == ComplianceState.REMEDIATION_GENERATED:
            self.retry_count += 1

        return True

    def is_terminal_state(self, state: Optional[ComplianceState] = None) -> bool:
        """Check if current state is terminal."""
        check_state = state or self.current_state
        return check_state in [ComplianceState.COMPLIANT, ComplianceState.UNRESOLVED]

    def get_transition_history(self, rule_id: Optional[str] = None) -> List[StateTransition]:
        """Get transition history, optionally filtered by rule."""
        if rule_id:
            return [t for t in self.transition_history if t.metadata.get('rule_id') == rule_id]
        return self.transition_history.copy()

    def reset(self):
        """Reset state manager to initial state."""
        self.current_state = ComplianceState.COMPLIANT
        self.retry_count = 0
        self.transition_history.clear()
        self.rule_states.clear()