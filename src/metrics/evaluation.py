"""Experimental Evaluation Framework - Collect and analyze measurable metrics.

Responsible for collecting and reporting:
1. Initial Compliance Rate
2. Autonomous Remediation Success Rate
3. Average Retry Count
4. Convergence Time
5. RAG ablation impact
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import time


@dataclass
class MetricSnapshot:
    """Single measurement of all metrics at a point in time."""
    timestamp: datetime
    rule_id: str
    initial_compliance: bool
    drift_count_initial: int
    drift_count_final: int
    attempts: int
    success: bool
    convergence_time_sec: float
    final_state: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "rule_id": self.rule_id,
            "initial_compliance": self.initial_compliance,
            "drift_count_initial": self.drift_count_initial,
            "drift_count_final": self.drift_count_final,
            "attempts": self.attempts,
            "success": self.success,
            "convergence_time_sec": self.convergence_time_sec,
            "final_state": self.final_state,
            "metadata": self.metadata
        }


class ExperimentalEvaluator:
    """Comprehensive metrics collection and analysis."""

    def __init__(self, output_dir: str = "./metrics_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.snapshots: List[MetricSnapshot] = []
        self.start_time = datetime.now()

    def collect_metrics(self, orchestrator, rule_id: str, initial_drift_count: int,
                       start_time: float) -> MetricSnapshot:
        """Collect metrics for a single rule after remediation attempt.

        Args:
            orchestrator: The Orchestrator instance
            rule_id: The rule being evaluated
            initial_drift_count: Number of drifts before remediation
            start_time: Time when remediation started (from time.time())

        Returns:
            MetricSnapshot with all metrics
        """
        end_time = time.time()
        convergence_time = end_time - start_time

        # Get current state and retry info
        current_state = orchestrator.state_manager.get_current_state(rule_id)
        retry_info = orchestrator.retry_controller.rule_attempts.get(rule_id, 0)

        # Re-audit to get final drift count
        try:
            final_audit = orchestrator.drift_auditor.audit_rule(rule_id)
            final_drift_count = len(final_audit.drifts)
            final_compliance = final_audit.is_compliant
        except Exception:
            final_drift_count = initial_drift_count
            final_compliance = False

        success = final_compliance and (initial_drift_count > 0)  # Success only if was non-compliant initially

        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            rule_id=rule_id,
            initial_compliance=(initial_drift_count == 0),
            drift_count_initial=initial_drift_count,
            drift_count_final=final_drift_count,
            attempts=retry_info,
            success=success,
            convergence_time_sec=convergence_time,
            final_state=current_state.value,
            metadata={
                "failure_pattern": orchestrator.retry_controller.get_failure_pattern(rule_id),
                "state_transitions": len(orchestrator.state_manager.get_transition_history(rule_id))
            }
        )

        self.snapshots.append(snapshot)
        return snapshot

    def get_initial_compliance_rate(self) -> float:
        """Calculate: Percentage of rules compliant before remediation."""
        if not self.snapshots:
            return 0.0

        compliant_initial = sum(1 for s in self.snapshots if s.initial_compliance)
        return compliant_initial / len(self.snapshots)

    def get_autonomous_success_rate(self) -> float:
        """Calculate: Percentage of drifts successfully resolved.

        Only counts rules that were initially non-compliant.
        """
        non_compliant = [s for s in self.snapshots if not s.initial_compliance]
        if not non_compliant:
            return 0.0

        successful = sum(1 for s in non_compliant if s.success)
        return successful / len(non_compliant)

    def get_average_retry_count(self) -> float:
        """Calculate: Average number of attempts per rule."""
        if not self.snapshots:
            return 0.0

        total_attempts = sum(s.attempts for s in self.snapshots)
        return total_attempts / len(self.snapshots)

    def get_average_convergence_time(self) -> float:
        """Calculate: Average time to convergence."""
        if not self.snapshots:
            return 0.0

        total_time = sum(s.convergence_time_sec for s in self.snapshots)
        return total_time / len(self.snapshots)

    def get_drift_resolution_rate(self) -> Dict[str, Any]:
        """Calculate: How many drifts were resolved per remediation attempt."""
        if not self.snapshots:
            return {}

        total_initial_drift = sum(s.drift_count_initial for s in self.snapshots)
        total_final_drift = sum(s.drift_count_final for s in self.snapshots)
        resolved = total_initial_drift - total_final_drift

        return {
            "total_initial_drifts": total_initial_drift,
            "total_final_drifts": total_final_drift,
            "total_resolved": resolved,
            "resolution_rate": resolved / total_initial_drift if total_initial_drift > 0 else 0.0
        }

    def get_failure_analysis(self) -> Dict[str, Any]:
        """Analyze failure patterns across all rules."""
        if not self.snapshots:
            return {}

        failure_counts = {}
        for snapshot in self.snapshots:
            if snapshot.metadata.get("failure_pattern"):
                pattern = snapshot.metadata["failure_pattern"]
                dist = pattern.get("failure_distribution", {})
                for failure_type, count in dist.items():
                    failure_counts[failure_type] = failure_counts.get(failure_type, 0) + count

        return {
            "failure_distribution": failure_counts,
            "total_failures": sum(failure_counts.values())
        }

    def get_state_transition_analysis(self) -> Dict[str, Any]:
        """Analyze state machine transitions."""
        if not self.snapshots:
            return {}

        final_states = {}
        for snapshot in self.snapshots:
            state = snapshot.final_state
            final_states[state] = final_states.get(state, 0) + 1

        return {
            "final_state_distribution": final_states,
            "compliant_final": final_states.get("compliant", 0),
            "unresolved": final_states.get("unresolved", 0)
        }

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report of all metrics."""
        return {
            "experiment_duration_sec": (datetime.now() - self.start_time).total_seconds(),
            "total_rules_evaluated": len(self.snapshots),
            "metrics": {
                "initial_compliance_rate_pct": self.get_initial_compliance_rate() * 100,
                "autonomous_success_rate_pct": self.get_autonomous_success_rate() * 100,
                "average_retry_count": self.get_average_retry_count(),
                "average_convergence_time_sec": self.get_average_convergence_time(),
                "drift_resolution": self.get_drift_resolution_rate()
            },
            "analysis": {
                "failure_patterns": self.get_failure_analysis(),
                "state_transitions": self.get_state_transition_analysis()
            }
        }

    def save_metrics_to_file(self, filename: str = "metrics_report.json"):
        """Save all metrics and report to JSON file."""
        report = self.generate_summary_report()
        output_path = self.output_dir / filename

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        return str(output_path)

    def save_detailed_metrics_to_file(self, filename: str = "metrics_detailed.json"):
        """Save detailed per-rule metrics to JSON file."""
        detailed = {
            "snapshots": [s.to_dict() for s in self.snapshots],
            "summary": self.generate_summary_report()
        }
        output_path = self.output_dir / filename

        with open(output_path, 'w') as f:
            json.dump(detailed, f, indent=2)

        return str(output_path)

    def print_summary(self):
        """Print human-readable summary to console."""
        report = self.generate_summary_report()

        print("\n" + "=" * 60)
        print("EXPERIMENTAL EVALUATION SUMMARY")
        print("=" * 60)
        print(f"\nExperiment Duration: {report['experiment_duration_sec']:.1f} seconds")
        print(f"Rules Evaluated: {report['total_rules_evaluated']}")

        print("\n--- Measurable Metrics ---")
        metrics = report['metrics']
        print(f"Initial Compliance Rate: {metrics['initial_compliance_rate_pct']:.1f}%")
        print(f"Autonomous Success Rate: {metrics['autonomous_success_rate_pct']:.1f}%")
        print(f"Average Retry Count: {metrics['average_retry_count']:.2f}")
        print(f"Average Convergence Time: {metrics['average_convergence_time_sec']:.2f}s")

        drift_res = metrics['drift_resolution']
        print(f"\nDrift Resolution:")
        print(f"  - Initial Drifts: {drift_res['total_initial_drifts']}")
        print(f"  - Final Drifts: {drift_res['total_final_drifts']}")
        print(f"  - Resolved: {drift_res['total_resolved']}")
        print(f"  - Resolution Rate: {drift_res['resolution_rate'] * 100:.1f}%")

        print("\n--- Failure Analysis ---")
        failures = report['analysis']['failure_patterns']
        if failures['failure_distribution']:
            for failure_type, count in failures['failure_distribution'].items():
                print(f"  {failure_type}: {count}")
        else:
            print("  No failures recorded")

        print("\n--- Final States ---")
        states = report['analysis']['state_transitions']['final_state_distribution']
        for state, count in states.items():
            print(f"  {state}: {count}")

        print("\n" + "=" * 60 + "\n")
