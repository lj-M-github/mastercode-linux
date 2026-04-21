"""Compliance Auditor module - Verify actual system state against CIS rule requirements.

执行后合规验证：在目标主机上运行 check_command，
用正则匹配实际输出，确认系统状态与合规要求一致。

运行环境：
  - SSH 模式：通过 SSHClient 连接真实目标主机（论文实验环境）
  - localhost 模式：使用 subprocess 直接在本机执行（开发测试）

Examples:
    >>> auditor = ComplianceAuditor("data/compliance_checks/cis_rhel9_checks.yaml")
    >>> result = auditor.audit_rule("5.2.1")
    >>> print(result.status, result.actual_output)

    >>> # SSH 模式
    >>> from src.executor.ssh_client import SSHClient, SSHConfig
    >>> client = SSHClient(SSHConfig(host="192.168.1.10", username="ansible"))
    >>> auditor = ComplianceAuditor("data/compliance_checks/cis_rhel9_checks.yaml",
    ...                             ssh_client=client)
    >>> results = auditor.audit_all(["5.2.1", "6.1.2", "4.1.1"])
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


@dataclass
class ComplianceCheckResult:
    """单条合规检查结果。

    Attributes:
        rule_id: CIS 规则编号（如 "5.2.1"）
        title: 规则标题
        domain: 安全域（ssh/filesystem/kernel/audit/firewall）
        severity: 严重程度（high/medium/low）
        status: 合规状态 — "pass" / "fail" / "skip"
        check_command: 执行的检查命令
        expected_pattern: 期望匹配的正则
        actual_output: 命令实际输出
        remediation_hint: 修复建议
        error: 执行错误信息（仅 skip 状态时有值）
    """
    rule_id: str
    title: str
    domain: str
    severity: str
    status: str                 # "pass" | "fail" | "skip"
    check_command: str
    expected_pattern: str
    actual_output: str = ""
    remediation_hint: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于 JSON 序列化。"""
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "domain": self.domain,
            "severity": self.severity,
            "status": self.status,
            "check_command": self.check_command,
            "expected_pattern": self.expected_pattern,
            "actual_output": self.actual_output,
            "remediation_hint": self.remediation_hint,
            "error": self.error,
        }


class ComplianceAuditor:
    """合规审计器。

    加载合规检查规范（YAML），并逐条在目标主机上验证系统实际配置。

    Attributes:
        checks_file: 合规检查规范文件路径
        ssh_client: SSHClient 实例（None 表示 localhost 模式）
        _checks: 加载的检查规范字典，key 为 rule_id
        _timeout: 单条命令超时（秒）

    Examples:
        >>> # localhost 模式
        >>> auditor = ComplianceAuditor(
        ...     "data/compliance_checks/cis_rhel9_checks.yaml"
        ... )
        >>> result = auditor.audit_rule("5.2.1")

        >>> # SSH 模式
        >>> from src.executor.ssh_client import SSHClient, SSHConfig
        >>> client = SSHClient(SSHConfig(host="10.0.0.5", username="ec2-user",
        ...                              key_file="~/.ssh/id_rsa"))
        >>> auditor = ComplianceAuditor(
        ...     "data/compliance_checks/cis_rhel9_checks.yaml",
        ...     ssh_client=client
        ... )
        >>> report = auditor.audit_all()
    """

    def __init__(
        self,
        checks_file: str,
        ssh_client=None,
        timeout: int = 15,
    ):
        """初始化合规审计器。

        Args:
            checks_file: 合规检查 YAML 规范文件路径
            ssh_client: SSHClient 实例；为 None 时在本机 localhost 执行
            timeout: 每条命令的最长等待时间（秒）
        """
        self.checks_file = Path(checks_file)
        self.ssh_client = ssh_client
        self._timeout = timeout
        self._checks: Dict[str, Dict[str, Any]] = {}
        self._load_checks()

    # ── 私有方法 ───────────────────────────────────────────────────────────

    def _load_checks(self) -> None:
        """从 YAML 文件加载合规检查规范。"""
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
        """在本机（localhost）执行 shell 命令。

        Args:
            command: shell 命令字符串

        Returns:
            (stdout, stderr) 元组
        """
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
        """通过 SSH 在远程主机执行命令。

        Args:
            command: shell 命令字符串

        Returns:
            (stdout, stderr) 元组
        """
        result = self.ssh_client.execute(command, timeout=self._timeout)
        return result.stdout.strip(), result.stderr.strip()

    def _run_command(self, command: str) -> tuple[str, str]:
        """执行命令（自动选择 SSH 或 localhost 模式）。"""
        if self.ssh_client is not None:
            return self._run_command_ssh(command)
        return self._run_command_local(command)

    def _match_output(self, output: str, pattern: str) -> bool:
        """用正则检验命令输出是否符合期望。

        Args:
            output: 命令实际输出
            pattern: 正则表达式

        Returns:
            True 表示合规（pass）
        """
        try:
            return bool(re.search(pattern, output, re.IGNORECASE | re.MULTILINE))
        except re.error:
            # 正则非法时回退到子串匹配
            return pattern.lower() in output.lower()

    # ── 公共接口 ───────────────────────────────────────────────────────────

    def audit_rule(self, rule_id: str) -> ComplianceCheckResult:
        """对单条规则执行合规检查。

        Args:
            rule_id: CIS 规则编号（如 "5.2.1"）

        Returns:
            ComplianceCheckResult 实例
        """
        check = self._checks.get(rule_id)
        if check is None:
            return ComplianceCheckResult(
                rule_id=rule_id,
                title="Unknown rule",
                domain="unknown",
                severity="unknown",
                status="skip",
                check_command="",
                expected_pattern="",
                error=f"No check specification found for rule_id={rule_id!r}",
            )

        cmd = check["check_command"]
        expected = check["expected_pattern"]
        stdout, stderr = self._run_command(cmd)

        if stderr and not stdout:
            # 命令执行失败，无法判断合规状态
            return ComplianceCheckResult(
                rule_id=rule_id,
                title=check.get("title", ""),
                domain=check.get("domain", ""),
                severity=check.get("severity", ""),
                status="skip",
                check_command=cmd,
                expected_pattern=expected,
                actual_output=stdout,
                remediation_hint=check.get("remediation_hint", ""),
                error=stderr,
            )

        matched = self._match_output(stdout, expected)
        return ComplianceCheckResult(
            rule_id=rule_id,
            title=check.get("title", ""),
            domain=check.get("domain", ""),
            severity=check.get("severity", ""),
            status="pass" if matched else "fail",
            check_command=cmd,
            expected_pattern=expected,
            actual_output=stdout,
            remediation_hint=check.get("remediation_hint", ""),
            error="",
        )

    def audit_all(
        self,
        rule_ids: Optional[List[str]] = None,
    ) -> List[ComplianceCheckResult]:
        """批量执行合规检查。

        Args:
            rule_ids: 要检查的规则 ID 列表；为 None 时检查所有已加载规则

        Returns:
            ComplianceCheckResult 列表，顺序与 rule_ids 一致
        """
        targets = rule_ids if rule_ids is not None else list(self._checks.keys())
        return [self.audit_rule(rid) for rid in targets]

    def summary(
        self,
        results: Optional[List[ComplianceCheckResult]] = None,
    ) -> Dict[str, Any]:
        """统计合规检查结果。

        Args:
            results: ComplianceCheckResult 列表；为 None 时自动运行 audit_all()

        Returns:
            包含 pass_count / fail_count / skip_count / pass_rate / by_domain / by_severity 的字典
        """
        if results is None:
            results = self.audit_all()

        pass_count = sum(1 for r in results if r.status == "pass")
        fail_count = sum(1 for r in results if r.status == "fail")
        skip_count = sum(1 for r in results if r.status == "skip")
        evaluable = pass_count + fail_count  # skip 不计入通过率分母

        pass_rate = (pass_count / evaluable) if evaluable > 0 else 0.0

        # 按安全域统计
        by_domain: Dict[str, Dict[str, int]] = {}
        for r in results:
            domain_stats = by_domain.setdefault(
                r.domain, {"pass": 0, "fail": 0, "skip": 0}
            )
            domain_stats[r.status] += 1

        # 按严重程度统计
        by_severity: Dict[str, Dict[str, int]] = {}
        for r in results:
            sev_stats = by_severity.setdefault(
                r.severity, {"pass": 0, "fail": 0, "skip": 0}
            )
            sev_stats[r.status] += 1

        return {
            "total": len(results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "skip_count": skip_count,
            "pass_rate": round(pass_rate, 4),
            "pass_rate_pct": f"{pass_rate * 100:.1f}%",
            "by_domain": by_domain,
            "by_severity": by_severity,
            "failed_rules": [r.rule_id for r in results if r.status == "fail"],
        }

    @property
    def available_rules(self) -> List[str]:
        """返回已加载的所有规则 ID。"""
        return list(self._checks.keys())
