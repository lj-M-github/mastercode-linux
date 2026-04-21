"""Experiment Runner — thesis-grade compliance remediation evaluation.

Usage:
    python experiments/run_experiment.py --num-runs 3 --num-rules 5 \\
        --output-dir ./thesis_experiments --target localhost
"""

import sys
import time
import json
import argparse
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main_agent import SecurityHardeningAgent


@dataclass
class RuleSnapshot:
    """Single-rule experimental observation."""
    rule_id: str
    initial_compliant: bool
    final_compliant: bool
    attempts: int
    success: bool
    final_state: str
    convergence_time_sec: float
    message: str


@dataclass
class ExperimentResult:
    name: str
    total_duration_sec: float
    remediation_duration_sec: float
    initial_compliant: int
    initial_non_compliant: int
    final_compliant: int
    final_non_compliant: int
    rules_fixed: int
    fix_rate_pct: float
    rule_snapshots: List[RuleSnapshot]


class ExperimentRunner:
    def __init__(self, output_dir: str = "./experiment_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.all_results: List[ExperimentResult] = []

    def run_single(self, agent: SecurityHardeningAgent,
                   rule_ids: List[str], target: str = "localhost",
                   name: str = "run_1") -> ExperimentResult:
        t0 = time.time()

        # Step 1: pre-audit
        print(f"\n  [{name}] Pre-audit ({len(rule_ids)} rules)...")
        pre = agent.audit_compliance(rule_ids)
        pre_compliant = pre["pass_count"]
        pre_non = pre["fail_count"]

        # Step 2: remediation
        print(f"  [{name}] Remediation...")
        r0 = time.time()
        result = agent.harden("SSH configuration compliance", target, rule_ids=rule_ids)
        remed_time = time.time() - r0

        # Step 3: post-audit
        print(f"  [{name}] Post-audit...")
        post = agent.audit_compliance(rule_ids)
        post_compliant = post["pass_count"]
        post_non = post["fail_count"]

        # Step 4: build snapshots
        results_map = {r["rule_id"]: r for r in result.get("results", [])}
        snapshots = []
        for rid in rule_ids:
            info = results_map.get(rid, {})
            snap = RuleSnapshot(
                rule_id=rid,
                initial_compliant=rid not in [r["rule_id"] for r in pre["results"] if not r.get("is_compliant", True)],
                final_compliant=rid not in [r["rule_id"] for r in post["results"] if not r.get("is_compliant", True)],
                attempts=info.get("attempts", 0),
                success=info.get("success", False),
                final_state=info.get("final_state", "unknown"),
                convergence_time_sec=remed_time / max(len(rule_ids), 1),
                message=info.get("message", ""),
            )
            snapshots.append(snap)

        total_time = time.time() - t0
        fixed = pre_non - post_non
        fix_rate = fixed / pre_non * 100 if pre_non > 0 else 0

        er = ExperimentResult(
            name=name, total_duration_sec=round(total_time, 2),
            remediation_duration_sec=round(remed_time, 2),
            initial_compliant=pre_compliant, initial_non_compliant=pre_non,
            final_compliant=post_compliant, final_non_compliant=post_non,
            rules_fixed=fixed, fix_rate_pct=round(fix_rate, 1),
            rule_snapshots=snapshots,
        )
        self.all_results.append(er)
        return er

    def run_multiple(self, agent: SecurityHardeningAgent,
                     rule_ids: List[str], target: str = "localhost",
                     num_runs: int = 3) -> List[ExperimentResult]:
        results = []
        for i in range(1, num_runs + 1):
            r = self.run_single(agent, rule_ids, target, f"run_{i}")
            results.append(r)
            print(f"  {r.name}: fixed {r.rules_fixed}/{r.initial_non_compliant} "
                  f"({r.fix_rate_pct}%) in {r.remediation_duration_sec}s")
        return results

    def save_report(self) -> Path:
        report = {
            "timestamp": datetime.now().isoformat(),
            "num_runs": len(self.all_results),
            "summary": {
                "avg_duration_sec": round(
                    sum(r.total_duration_sec for r in self.all_results) / max(len(self.all_results), 1), 2),
                "avg_remediation_sec": round(
                    sum(r.remediation_duration_sec for r in self.all_results) / max(len(self.all_results), 1), 2),
                "avg_fix_rate_pct": round(
                    sum(r.fix_rate_pct for r in self.all_results) / max(len(self.all_results), 1), 2),
                "avg_rules_fixed": round(
                    sum(r.rules_fixed for r in self.all_results) / max(len(self.all_results), 1), 2),
            },
            "runs": [asdict(r) for r in self.all_results],
        }
        fp = self.output_dir / f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        fp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return fp


def main():
    parser = argparse.ArgumentParser(description="Run compliance remediation experiments")
    parser.add_argument("--output-dir", type=str, default="./thesis_experiments")
    parser.add_argument("--target", type=str, default="localhost")
    parser.add_argument("--num-rules", type=int, default=5)
    parser.add_argument("--num-runs", type=int, default=3)
    parser.add_argument("--doc-dir", type=str, default="./data")
    args = parser.parse_args()

    # ── Agent setup ────────────────────────────────────────────────
    config = {
        "db_path": "./vector_db",
        "model_name": "all-MiniLM-L6-v2",
        "llm_model": "deepseek-chat",
        "playbook_dir": "./playbooks",
        "report_dir": "./reports",
        "audit_dir": "./audit_logs",
        "compliance_checks_file": "./data/compliance_checks/cis_rhel9_checks.yaml",
    }
    agent = SecurityHardeningAgent(config)

    # ── Knowledge ingestion ────────────────────────────────────────
    print("=" * 60)
    print("COMPLIANCE REMEDIATION EXPERIMENT")
    print("=" * 60)
    print(f"  Target Host: {args.target}")
    print(f"  Rules to Test: {args.num_rules}")
    print(f"  Runs: {args.num_runs}")
    print(f"  Output: {args.output_dir}")

    if Path(args.doc_dir).exists():
        print(f"\n  Ingesting knowledge from {args.doc_dir}...")
        try:
            ingest_result = agent.ingest_knowledge(args.doc_dir)
            print(f"  Ingested: {ingest_result.get('items_added', 0)} items")
        except Exception as e:
            print(f"  Warning: knowledge ingestion failed: {e}")

    # ── Rule selection ─────────────────────────────────────────────
    test_rules = [f"5.2.{i}" for i in range(1, min(args.num_rules + 1, 6))]
    print(f"  Rules: {test_rules}")
    print("=" * 60)

    # ── Execute ────────────────────────────────────────────────────
    runner = ExperimentRunner(output_dir=args.output_dir)
    try:
        results = runner.run_multiple(agent, test_rules, args.target, args.num_runs)
        fp = runner.save_report()
        print(f"\n{'=' * 60}")
        print("EXPERIMENT COMPLETED")
        print(f"{'=' * 60}")
        for r in results:
            print(f"  {r.name}: {r.rules_fixed}/{r.initial_non_compliant} fixed "
                  f"({r.fix_rate_pct}%) in {r.remediation_duration_sec}s")
        print(f"\n  Report: {fp}")
        print(f"{'=' * 60}\n")
    except Exception as e:
        print(f"\n  EXPERIMENT FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
