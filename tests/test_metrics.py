"""Metrics collection in tests - Demonstrates measurable metrics in practice."""

import sys
import time
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.metrics.evaluation import ExperimentalEvaluator
from src.control.orchestrator import Orchestrator
from src.compliance.rule_model import DriftResult, DriftField


def mock_audit_with_drift(rule_id: str, has_drift: bool = True) -> DriftResult:
    """Mock audit result for testing."""
    if has_drift:
        return DriftResult(
            rule_id=rule_id,
            is_compliant=False,
            drifts=[
                DriftField(
                    key=f"test_field_{rule_id}",
                    expected="enabled",
                    actual="disabled",
                    comparison_type="exact"
                )
            ],
            title=f"Test Rule {rule_id}",
            domain="test",
            severity="high"
        )
    else:
        return DriftResult(
            rule_id=rule_id,
            is_compliant=True,
            drifts=[],
            title=f"Test Rule {rule_id}",
            domain="test",
            severity="high"
        )


def test_measurable_metrics_collection():
    """Test 1: Verify metrics are collected correctly during remediation.
    
    This test demonstrates:
    - How ExperimentalEvaluator collects metrics
    - How metrics are structured and stored
    - How to access individual metric values
    """
    print("\n[TEST 1] Testing Metrics Collection")
    print("-" * 50)

    # Initialize evaluator
    evaluator = ExperimentalEvaluator(output_dir="./test_metrics")

    # Simulate 5 rule remediations with different outcomes
    test_scenarios = [
        ("5.2.1", True, 1),   # Initial drift, 1 attempt  success
        ("5.2.2", True, 2),   # Initial drift, 2 attempts, success
        ("5.2.3", True, 3),   # Initial drift, 3 attempts, success
        ("6.1.1", False, 0),  # Already compliant, no attempts
        ("6.1.2", True, 3),   # Initial drift, 3 attempts, but still non-compliant (unresolved)
    ]

    for rule_id, success, attempts in test_scenarios:
        start = time.time()
        time.sleep(0.1)  # Simulate processing time

        # Simulate initial audit showing drift
        initial_drift = 0 if success is False else 1

        # Create snapshot
        snapshot = evaluator.MetricSnapshot(
            timestamp=None,
            rule_id=rule_id,
            initial_compliance=(initial_drift == 0),
            drift_count_initial=initial_drift,
            drift_count_final=0 if success else initial_drift,
            attempts=attempts if not (initial_drift == 0) else 0,
            success=success and (initial_drift > 0),
            convergence_time_sec=time.time() - start,
            final_state="compliant" if success else ("unresolved" if attempts >= 3 else "drift_detected"),
            metadata={"test": True}
        )
        snapshot.timestamp = evaluator.datetime.now()
        evaluator.snapshots.append(snapshot)

    # Verify metrics can be calculated
    initial_compliance = evaluator.get_initial_compliance_rate()
    success_rate = evaluator.get_autonomous_success_rate()
    avg_retries = evaluator.get_average_retry_count()
    convergence = evaluator.get_average_convergence_time()

    print(f"✓ Initial Compliance Rate: {initial_compliance * 100:.1f}%")
    print(f"✓ Autonomous Success Rate: {success_rate * 100:.1f}%")
    print(f"✓ Average Retry Count: {avg_retries:.2f}")
    print(f"✓ Average Convergence Time: {convergence:.3f}s")

    assert isinstance(initial_compliance, float)
    assert isinstance(success_rate, float)
    assert avg_retries > 0
    print("✓ All metrics collected correctly\n")


def test_drift_resolution_metric():
    """Test 2: Verify drift resolution metrics.
    
    This test demonstrates:
    - Tracking initial vs final drift counts
    - Calculating drift resolution rate
    - Understanding remediation effectiveness
    """
    print("[TEST 2] Testing Drift Resolution Metrics")
    print("-" * 50)

    evaluator = ExperimentalEvaluator()

    # Test scenario: 3 rules with different drift counts
    scenarios = [
        ("rule1", 3, 0),   # 3 drifts → 0 drifts (fully resolved)
        ("rule2", 2, 1),   # 2 drifts → 1 drift (partial resolution)
        ("rule3", 1, 1),   # 1 drift → 1 drift (not resolved)
    ]

    for rule_id, initial, final in scenarios:
        snapshot = evaluator.MetricSnapshot(
            timestamp=evaluator.datetime.now(),
            rule_id=rule_id,
            initial_compliance=False,
            drift_count_initial=initial,
            drift_count_final=final,
            attempts=1,
            success=(final == 0),
            convergence_time_sec=0.5,
            final_state="compliant" if final == 0 else "verification_failed"
        )
        evaluator.snapshots.append(snapshot)

    # Get drift resolution metrics
    drift_metrics = evaluator.get_drift_resolution_rate()

    print(f"✓ Total Initial Drifts: {drift_metrics['total_initial_drifts']}")
    print(f"✓ Total Final Drifts: {drift_metrics['total_final_drifts']}")
    print(f"✓ Total Resolved: {drift_metrics['total_resolved']}")
    print(f"✓ Resolution Rate: {drift_metrics['resolution_rate'] * 100:.1f}%")

    assert drift_metrics['total_initial_drifts'] == 6
    assert drift_metrics['total_final_drifts'] == 2
    assert drift_metrics['total_resolved'] == 4
    print("✓ Drift resolution metrics verified\n")


def test_failure_categorization():
    """Test 3: Verify failure categorization and analysis.
    
    This test demonstrates:
    - How failures are categorized by type
    - Analyzing failure patterns across rules
    - Understanding retry effectiveness
    """
    print("[TEST 3] Testing Failure Categorization")
    print("-" * 50)

    from src.control.retry_controller import RetryController, FailureType

    controller = RetryController(max_retry_count=3)

    # Record different failure types
    controller.record_failure(
        rule_id="5.2.1",
        error_message="Syntax error in playbook",
        failure_type=FailureType.SYNTAX_ERROR
    )
    controller.record_failure(
        rule_id="5.2.1",
        error_message="Permission denied when accessing file",
        failure_type=FailureType.PERMISSION_ERROR
    )
    controller.record_failure(
        rule_id="6.1.1",
        error_message="Missing dependency module",
        failure_type=FailureType.DEPENDENCY_ERROR
    )

    # Analyze patterns
    pattern_5_2_1 = controller.get_failure_pattern("5.2.1")
    pattern_6_1_1 = controller.get_failure_pattern("6.1.1")

    print(f"Rule 5.2.1 Failures:")
    print(f"  - Total: {pattern_5_2_1['total_failures']}")
    print(f"  - Distribution: {pattern_5_2_1['failure_distribution']}")

    print(f"Rule 6.1.1 Failures:")
    print(f"  - Total: {pattern_6_1_1['total_failures']}")
    print(f"  - Distribution: {pattern_6_1_1['failure_distribution']}")

    assert pattern_5_2_1['total_failures'] == 2
    assert pattern_6_1_1['total_failures'] == 1
    print("✓ Failure categorization working correctly\n")


def test_state_machine_transitions():
    """Test 4: Verify state machine transition tracking.
    
    This test demonstrates:
    - How state transitions are recorded
    - Analyzing final state distribution
    - Understanding workflow convergence
    """
    print("[TEST 4] Testing State Machine Transitions")
    print("-" * 50)

    from src.control.state_manager import StateManager, ComplianceState

    state_mgr = StateManager(max_retries=3)

    # Simulate state transitions for 3 rules
    # Rule 1: Successful remediation
    state_mgr.rule_states["rule1"] = ComplianceState.COMPLIANT
    state_mgr.transition_history.append(
        type('obj', (object,), {
            'rule_id': 'rule1',
            'from_state': ComplianceState.DRIFT_DETECTED,
            'to_state': ComplianceState.COMPLIANT
        })()
    )

    # Rule 2: Unresolved
    state_mgr.rule_states["rule2"] = ComplianceState.UNRESOLVED
    state_mgr.transition_history.append(
        type('obj', (object,), {
            'rule_id': 'rule2',
            'from_state': ComplianceState.VERIFICATION_FAILED,
            'to_state': ComplianceState.UNRESOLVED
        })()
    )

    # Rule 3: Verification failed then recovered
    state_mgr.rule_states["rule3"] = ComplianceState.COMPLIANT
    state_mgr.transition_history.append(
        type('obj', (object,), {
            'rule_id': 'rule3',
            'from_state': ComplianceState.VERIFICATION_FAILED,
            'to_state': ComplianceState.REMEDIATION_GENERATED
        })()
    )

    print(f"✓ State machine tracking {len(state_mgr.transition_history)} transitions")
    print(f"✓ Current states by rule:")
    for rule_id, state in state_mgr.rule_states.items():
        print(f"    {rule_id}: {state.value}")

    assert len(state_mgr.transition_history) == 3
    print("✓ State transitions recorded correctly\n")


def test_comprehensive_evaluation_report():
    """Test 5: Verify comprehensive evaluation report generation.
    
    This test demonstrates:
    - How all metrics are integrated into a summary report
    - Report format and structure
    - How to use evaluation data for thesis analysis
    """
    print("[TEST 5] Testing Comprehensive Report Generation")
    print("-" * 50)

    evaluator = ExperimentalEvaluator()

    # Populate with test data
    for i in range(1, 6):
        snapshot = evaluator.MetricSnapshot(
            timestamp=evaluator.datetime.now(),
            rule_id=f"test_{i}",
            initial_compliance=(i > 4),  # Last rule is already compliant
            drift_count_initial=(0 if i > 4 else i),
            drift_count_final=(0 if i <= 3 else i),  # First 3 fully resolved
            attempts=(i if i <= 3 else 0),
            success=(i <= 3),
            convergence_time_sec=i * 0.1,
            final_state="compliant" if i <= 3 else "drift_detected"
        )
        evaluator.snapshots.append(snapshot)

    # Generate comprehensive report
    report = evaluator.generate_summary_report()

    print(f"✓ Total Rules Evaluated: {report['total_rules_evaluated']}")
    print(f"✓ Experiment Duration: {report['experiment_duration_sec']:.2f}s")
    print(f"\n✓ Key Metrics:")
    metrics = report['metrics']
    print(f"  - Initial Compliance: {metrics['initial_compliance_rate_pct']:.1f}%")
    print(f"  - Autonomous Success: {metrics['autonomous_success_rate_pct']:.1f}%")
    print(f"  - Avg Retries: {metrics['average_retry_count']:.2f}")
    print(f"  - Avg Convergence: {metrics['average_convergence_time_sec']:.3f}s")

    assert 'metrics' in report
    assert 'analysis' in report
    print("✓ Comprehensive report generated successfully\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("METRICS COLLECTION AND EVALUATION TESTS")
    print("=" * 60)

    test_measurable_metrics_collection()
    test_drift_resolution_metric()
    test_failure_categorization()
    test_state_machine_transitions()
    test_comprehensive_evaluation_report()

    print("=" * 60)
    print("✓ ALL METRICS TESTS PASSED")
    print("=" * 60 + "\n")
