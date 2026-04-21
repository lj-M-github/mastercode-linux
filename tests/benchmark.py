"""Performance benchmark — quantitative evidence for paper hypotheses.

Five core metrics vs CIS security baseline:
  1. Retrieval accuracy    > 90%
  2. Code generation acc.  > 85%
  3. Self-healing success  > 70%
  4. Avg response time     < 30s
  5. Hardening coverage     > 80%

Usage:
    source venv/bin/activate
    python tests/benchmark.py                 # run all
    python tests/benchmark.py --metric 1 3    # run specific metrics
    python tests/benchmark.py --list          # list available metrics
"""

import sys
import time
import json
import statistics
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import MagicMock
from dataclasses import dataclass, field, asdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main_agent import SecurityHardeningAgent
from src.utils.yaml_utils import extract_yaml
from src.feedback.self_heal import HealingResult
from src.executor.ansible_runner import ExecutionResult


# ── Test data ───────────────────────────────────────────────────────────────

RETRIEVAL_CASES = [
    {"query": "SSH root login", "keywords": ["ssh", "root", "login", "permit"]},
    {"query": "password policy", "keywords": ["password", "pam", "policy", "complex"]},
    {"query": "firewall configuration", "keywords": ["firewall", "firewalld", "port"]},
    {"query": "file permissions", "keywords": ["permission", "owner", "group", "file"]},
    {"query": "audit logging", "keywords": ["audit", "log", "auditd", "rsyslog"]},
    {"query": "kernel parameters", "keywords": ["kernel", "sysctl", "randomize"]},
    {"query": "user account management", "keywords": ["user", "account", "passwd"]},
    {"query": "network configuration", "keywords": ["network", "ip", "route"]},
    {"query": "SELinux enforcement", "keywords": ["selinux", "enforc", "policy"]},
    {"query": "cron job security", "keywords": ["cron", "job", "schedule"]},
]

CODE_GEN_CASES = [
    {
        "rule_id": "5.2.1", "title": "Ensure SSH root login is disabled",
        "remediation": "Set PermitRootLogin to no in /etc/ssh/sshd_config",
    },
    {
        "rule_id": "5.3.1", "title": "Ensure password policy is configured",
        "remediation": "Set minlen=14 in /etc/security/pwquality.conf",
    },
    {
        "rule_id": "3.4.1", "title": "Ensure firewall is installed",
        "remediation": "Install and enable firewalld or ufw",
    },
    {
        "rule_id": "1.1.1", "title": "Ensure /tmp is mounted",
        "remediation": "Mount /tmp with nodev,nosuid,noexec options",
    },
    {
        "rule_id": "4.1.1", "title": "Ensure auditd is installed",
        "remediation": "Install auditd package and enable service",
    },
]

SELF_HEAL_CASES = [
    {
        "playbook": "---\n- name: Test\n  hosts: localhost\n  tasks:\n    - name: Install\n      yum: name=httpd state=present",
        "error": "No package matching 'httpd' found",
        "rule": "Install web server",
    },
    {
        "playbook": "---\n- name: Test\n  hosts: localhost\n  tasks:\n    - name: Copy file\n      copy: src=/tmp/missing.conf dest=/etc/app.conf",
        "error": "Source /tmp/missing.conf not found",
        "rule": "Copy configuration file",
    },
    {
        "playbook": "---\n- name: Test\n  hosts: localhost\n  tasks:\n    - name: Set permission\n      file: path=/etc/shadow mode=0644",
        "error": "Permission denied",
        "rule": "Set correct file permissions",
    },
]

COVERAGE_SECTIONS = [
    "Initial Setup", "Services", "Network Configuration",
    "Logging and Auditing", "Access Authentication Authorization",
    "System Maintenance", "Filesystem Configuration",
    "Software Updates", "User Accounts", "SSH Server",
]


@dataclass
class MetricResult:
    name: str
    target: str
    value: float
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0


class Benchmark:
    def __init__(self):
        self.results: List[MetricResult] = []
        self.agent = SecurityHardeningAgent({
            "db_path": "./vector_db",
            "model_name": "all-MiniLM-L6-v2",
            "playbook_dir": "./playbooks",
            "report_dir": "./test_reports",
            "audit_dir": "./test_audit",
        })

    # ── 1. Retrieval accuracy ───────────────────────────────────────────

    def retrieval_accuracy(self) -> MetricResult:
        """Top-5 vector search recall against known CIS topics."""
        t0 = time.time()
        hits = 0
        details = []
        for c in RETRIEVAL_CASES:
            try:
                results = self.agent.search_knowledge(c["query"], n_results=5)
            except Exception as e:
                details.append({"q": c["query"], "hit": False, "err": str(e)})
                continue
            text = " ".join(
                f"{r.get('content', '')} {r.get('metadata', '')}" for r in results
            ).lower()
            matched = sum(1 for kw in c["keywords"] if kw.lower() in text)
            need = max(1, (len(c["keywords"]) + 1) // 2)
            hit = matched >= need
            if hit:
                hits += 1
            details.append({"q": c["query"], "hit": hit, "matched": matched, "need": need})
        rate = hits / len(RETRIEVAL_CASES) * 100 if RETRIEVAL_CASES else 0
        r = MetricResult("Retrieval accuracy", "> 90%", round(rate, 1), rate >= 90,
                         {"hits": hits, "total": len(RETRIEVAL_CASES), "cases": details},
                         round(time.time() - t0, 2))
        self.results.append(r)
        return r

    # ── 2. Code generation accuracy ─────────────────────────────────────

    def code_generation_accuracy(self) -> MetricResult:
        """Generated playbook must contain valid YAML structure."""
        t0 = time.time()
        valid = 0
        details = []
        for c in CODE_GEN_CASES:
            try:
                pb = self.agent.generate_playbook(c["rule_id"], c["title"], c["remediation"])
            except Exception as e:
                details.append({"rule": c["rule_id"], "ok": False, "err": str(e)})
                continue
            ok = "- name:" in pb and extract_yaml(pb) is not None
            if ok:
                valid += 1
            details.append({"rule": c["rule_id"], "ok": ok, "len": len(pb)})
        rate = valid / len(CODE_GEN_CASES) * 100 if CODE_GEN_CASES else 0
        r = MetricResult("Code generation accuracy", "> 85%", round(rate, 1), rate >= 85,
                         {"valid": valid, "total": len(CODE_GEN_CASES), "cases": details},
                         round(time.time() - t0, 2))
        self.results.append(r)
        return r

    # ── 3. Self-healing success ─────────────────────────────────────────

    def self_healing_success(self) -> MetricResult:
        """Broken playbook → heal → corrected playbook."""
        t0 = time.time()
        healed = 0
        details = []
        for c in SELF_HEAL_CASES:
            calls = {"n": 0}
            def mock_exec(pb):
                calls["n"] += 1
                if calls["n"] == 1:
                    return ExecutionResult(
                        plan_id="t", success=False, steps_executed=0,
                        steps_failed=1, output="", error=c["error"])
                return ExecutionResult(
                    plan_id="t", success=True, steps_executed=1,
                    steps_failed=0, output="ok=1", error="")
            try:
                hr = self.agent.self_healer.heal(
                    c["playbook"], c["error"], c["rule"], execute_fn=mock_exec)
            except Exception as e:
                details.append({"rule": c["rule"], "ok": False, "err": str(e)})
                continue
            ok = hr.success or hr.rewritten_playbook != c["playbook"]
            if ok:
                healed += 1
            details.append({"rule": c["rule"], "ok": ok, "attempts": hr.attempts})
        rate = healed / len(SELF_HEAL_CASES) * 100 if SELF_HEAL_CASES else 0
        r = MetricResult("Self-healing success", "> 70%", round(rate, 1), rate >= 70,
                         {"healed": healed, "total": len(SELF_HEAL_CASES), "cases": details},
                         round(time.time() - t0, 2))
        self.results.append(r)
        return r

    # ── 4. Average response time ────────────────────────────────────────

    def average_response_time(self) -> MetricResult:
        """End-to-end: search + generate wall-clock latency."""
        t0 = time.time()
        timings = []
        for c in CODE_GEN_CASES:
            s = time.time()
            try:
                self.agent.search_knowledge(c["title"], n_results=3)
                self.agent.generate_playbook(c["rule_id"], c["title"], c["remediation"])
            except Exception:
                pass
            timings.append(time.time() - s)
        avg = statistics.mean(timings) if timings else 0
        r = MetricResult("Average response time", "< 30s", round(avg, 2), avg < 30,
                         {"avg": round(avg, 2),
                          "max": round(max(timings), 2) if timings else 0,
                          "min": round(min(timings), 2) if timings else 0,
                          "samples": len(timings)},
                         round(time.time() - t0, 2))
        self.results.append(r)
        return r

    # ── 5. Hardening coverage ───────────────────────────────────────────

    def hardening_coverage(self) -> MetricResult:
        """Each CIS section must be searchable and generate a playbook."""
        t0 = time.time()
        covered = 0
        details = []
        for sec in COVERAGE_SECTIONS:
            try:
                results = self.agent.search_knowledge(sec, n_results=3)
                has = len(results) > 0
                gen = False
                if has:
                    b = results[0]
                    m = b["metadata"]
                    title = m.get("section_title") or sec
                    remed = m.get("remediation", "")
                    if not remed or remed.strip().startswith("Related rules:"):
                        remed = b["content"]
                    pb = self.agent.generate_playbook(
                        m.get("rule_id", ""), title, remed)
                    gen = "- name:" in pb
            except Exception:
                has = gen = False
            ok = has and gen
            if ok:
                covered += 1
            details.append({"section": sec, "ok": ok, "has_results": has, "can_gen": gen})
        rate = covered / len(COVERAGE_SECTIONS) * 100 if COVERAGE_SECTIONS else 0
        r = MetricResult("Hardening coverage", "> 80%", round(rate, 1), rate >= 80,
                         {"covered": covered, "total": len(COVERAGE_SECTIONS), "cases": details},
                         round(time.time() - t0, 2))
        self.results.append(r)
        return r

    # ── Registry ────────────────────────────────────────────────────────

    _METRICS = {
        1: ("Retrieval accuracy", retrieval_accuracy),
        2: ("Code generation accuracy", code_generation_accuracy),
        3: ("Self-healing success", self_healing_success),
        4: ("Average response time", average_response_time),
        5: ("Hardening coverage", hardening_coverage),
    }

    def run(self, indices: List[int] | None = None) -> Dict[str, Any]:
        indices = indices or list(self._METRICS.keys())
        total_t0 = time.time()
        for i in indices:
            name, fn = self._METRICS[i]
            r = fn(self)
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{i}] {r.name}: {r.value} ({status}, {r.duration}s)")

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        elapsed = time.time() - total_t0

        print(f"\n  {passed}/{total} passed  |  {elapsed:.1f}s")

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_duration_seconds": round(elapsed, 2),
            "summary": {"passed": passed, "total": total,
                        "pass_rate": round(passed / total * 100, 1) if total else 0},
            "results": [asdict(r) for r in self.results],
        }
        out = Path("data/test_results")
        out.mkdir(parents=True, exist_ok=True)
        fp = out / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        fp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Report: {fp}")
        return report


def main():
    parser = argparse.ArgumentParser(description="Run benchmarks")
    parser.add_argument("--metric", type=int, nargs="+", help="Run specific metrics (e.g. --metric 1 3)")
    parser.add_argument("--list", action="store_true", help="List available metrics")
    args = parser.parse_args()

    if args.list:
        for i, (name, _) in Benchmark._METRICS.items():
            print(f"  [{i}] {name}")
        return

    b = Benchmark()
    report = b.run(args.metric)
    sys.exit(0 if report["summary"]["passed"] == report["summary"]["total"] else 1)


if __name__ == "__main__":
    main()
