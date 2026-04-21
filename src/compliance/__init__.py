"""Compliance module — deterministic rule-driven audit and drift detection."""

from .auditor import ComplianceAuditor, ComplianceCheckResult
from .rule_model import (
	DriftField,
	DriftResult,
	COMPARISON_REGEX_MATCH,
	COMPARISON_EXACT,
	COMPARISON_CONTAINS,
	COMPARISON_NOT_CONTAINS,
	VALID_COMPARISON_TYPES,
)
from .drift_auditor import DriftAuditor

__all__ = [
	# Legacy auditor (boolean pass/fail)
	"ComplianceAuditor",
	"ComplianceCheckResult",
	# Drift model
	"DriftField",
	"DriftResult",
	"COMPARISON_REGEX_MATCH",
	"COMPARISON_EXACT",
	"COMPARISON_CONTAINS",
	"COMPARISON_NOT_CONTAINS",
	"VALID_COMPARISON_TYPES",
	# Deterministic drift auditor
	"DriftAuditor",
]
