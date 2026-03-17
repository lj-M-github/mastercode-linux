"""Ansible 执行模块 - 用于执行安全加固操作。

本模块负责执行 Ansible 剧本和加固步骤，收集执行结果，
并提供执行反馈给上层代理模块。
"""

import subprocess
import json
import tempfile
from dataclasses import dataclass, field
import re
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

@dataclass
class HardeningStep:
    """单个加固步骤。

    Attributes:
        name: 步骤名称
        module: Ansible 模块名称
        params: 模块参数
        when: 执行条件
    """
    name: str
    module: str
    params: Dict[str, Any] = field(default_factory=dict)
    when: str = ""


@dataclass
class HardeningPlan:
    """加固计划，包含多个步骤。

    Attributes:
        plan_id: 计划 ID
        rule_id: 规则 ID
        description: 计划描述
        steps: 步骤列表
        target_host: 目标主机
    """
    plan_id: str
    rule_id: str
    description: str
    steps: List[HardeningStep] = field(default_factory=list)
    target_host: str = "localhost"


@dataclass
class ExecutionResult:
    """执行结果数据类。

    存储 Ansible 执行操作的返回结果。

    Attributes:
        plan_id: 计划或步骤标识符
        success: 执行是否成功
        steps_executed: 成功执行的步骤数
        steps_failed: 失败的步骤数
        output: 标准输出内容
        error: 错误输出内容
        duration_seconds: 执行耗时（秒）
        timestamp: 执行时间戳（ISO 格式）

    Examples:
        >>> result = ExecutionResult("1.1", True, 5, 0, "ok=5 changed=0")
        >>> print(result)
        ExecutionResult[SUCCESS] 1.1: 5 steps executed
    """
    plan_id: str
    success: bool
    steps_executed: int
    steps_failed: int
    output: str
    error: str = ""
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __str__(self) -> str:
        """返回执行结果的字符串表示。"""
        status = "SUCCESS" if self.success else "FAILED"
        return f"ExecutionResult[{status}] {self.plan_id}: {self.steps_executed} 步骤已执行"


class AnsibleRunner:
    """Ansible 剧本执行器。

    负责执行 Ansible 剧本和单个加固步骤。

    Attributes:
        playbook_dir: 剧本目录路径
        verbose: 是否启用详细输出
        _last_output: 上次执行的输出行列表

    注意:
        执行需要系统已安装 Ansible，并且 ansible-playbook 命令在 PATH 中可用。
    """

    def __init__(
        self,
        playbook_dir: str = "./playbooks",
        verbose: bool = False
    ):
        """初始化 Ansible 执行器。

        Args:
            playbook_dir: Ansible 剧本存放目录，默认"./playbooks"
            verbose: 是否启用详细输出模式，默认 False
        """
        self.playbook_dir = Path(playbook_dir)
        self.verbose = verbose
        self._last_output: List[str] = []

    def run_playbook(
        self,
        playbook_name: str,
        extra_vars: Optional[Dict[str, Any]] = None,
        limit: Optional[str] = None
    ) -> ExecutionResult:
        """执行 Ansible 剧本。

        构建 ansible-playbook 命令并执行，捕获输出和错误。

        Args:
            playbook_name: 剧本文件名（相对于 playbook_dir）
            extra_vars: 额外变量字典，通过 -e 参数传递
            limit: 限制执行的主机模式，如"webserver"或"*.example.com"

        Returns:
            ExecutionResult 对象，包含执行结果

        执行状态说明:
            - success=True: 剧本执行成功（返回码为 0）
            - steps_executed: ok= 和 changed= 的总数
            - steps_failed: failed= 和 unreachable= 的总数

        错误处理:
            - 剧本文件不存在：返回 success=False，error 包含"Playbook not found"
            - 执行超时（300 秒）：返回 success=False，error 包含"timed out"
            - ansible-playbook 未找到：返回 success=False，error 包含"command not found"
        """
        playbook_path = self.playbook_dir / playbook_name

        # 检查剧本文件是否存在
        if not playbook_path.exists():
            return ExecutionResult(
                plan_id=playbook_name,
                success=False,
                steps_executed=0,
                steps_failed=0,
                output="",
                error=f"剧本不存在：{playbook_path}"
            )

        # 构建命令
        cmd = ["ansible-playbook", str(playbook_path)]

        # 添加额外变量
        if extra_vars:
            cmd.extend(["-e", json.dumps(extra_vars)])

        # 限制主机
        if limit:
            cmd.extend(["--limit", limit])

        # 详细输出
        if self.verbose:
            cmd.append("-v")

        try:
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 分钟超时
            )
            self._last_output = result.stdout.splitlines()

            return ExecutionResult(
                plan_id=playbook_name,
                success=result.returncode == 0,
                steps_executed=self._count_successful_steps(result.stdout),
                steps_failed=self._count_failed_steps(result.stdout + "\n" + result.stderr),
                output=result.stdout,
                error=result.stderr,
                duration_seconds=0.0
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                plan_id=playbook_name,
                success=False,
                steps_executed=0,
                steps_failed=0,
                output="",
                error="剧本执行超时（超过 300 秒）"
            )
        except FileNotFoundError:
            return ExecutionResult(
                plan_id=playbook_name,
                success=False,
                steps_executed=0,
                steps_failed=0,
                output="",
                error="未找到 ansible-playbook 命令，请确保已安装 Ansible"
            )

    def _count_successful_steps(self, output: str) -> int:
        """从 Ansible 输出中统计成功步骤数。

        统计 ok= 和 changed= 的出现次数。

        Args:
            output: Ansible 标准输出

        Returns:
            成功步骤数
        """
        recap = self._extract_recap_totals(output)
        return recap["ok"] + recap["changed"]

    def _count_failed_steps(self, output: str) -> int:
        """从 Ansible 输出中统计失败步骤数。

        统计 failed= 和 unreachable= 的出现次数。

        Args:
            output: Ansible 错误输出

        Returns:
            失败步骤数
        """
        recap = self._extract_recap_totals(output)
        return recap["failed"] + recap["unreachable"]

    def _extract_recap_totals(self, text: str) -> Dict[str, int]:
        """提取并聚合 recap 值，支持多主机输出。

        Args:
            text: Ansible 输出文本

        Returns:
            包含 ok, changed, failed, unreachable 的字典
        """
        totals = {
            "ok": 0,
            "changed": 0,
            "failed": 0,
            "unreachable": 0,
        }

        for key, value in re.findall(r"(ok|changed|failed|unreachable)=(\d+)", text):
            totals[key] += int(value)

        return totals

    def execute(
        self,
        playbook_content: str,
        target_host: str = "localhost"
    ) -> ExecutionResult:
        """执行 Playbook 内容（临时文件）。

        Args:
            playbook_content: Playbook YAML 内容
            target_host: 目标主机

        Returns:
            ExecutionResult 对象
        """
        # 写入临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yml',
            delete=False
        ) as f:
            f.write(playbook_content)
            temp_playbook = f.name

        try:
            # Respect target_host by forwarding it as --limit when provided.
            # Keep localhost behavior unchanged when target_host is empty.
            limit = target_host if target_host else None
            return self.run_playbook(
                temp_playbook,
                limit=limit
            )
        finally:
            # 清理临时文件
            Path(temp_playbook).unlink()

    def run_step(
        self,
        step: HardeningStep,
        target_host: str = "localhost"
    ) -> ExecutionResult:
        """执行单个加固步骤。

        为单个步骤创建临时剧本并执行。

        Args:
            step: HardeningStep 对象，包含步骤详情
            target_host: 目标主机，默认"localhost"

        Returns:
            ExecutionResult 对象，包含执行结果

        注意:
            临时剧本文件在执行后会自动删除
        """
        # 创建临时剧本内容
        playbook_content = self._create_step_playbook(step, target_host)

        # 写入临时文件并执行
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yml',
            delete=False
        ) as f:
            f.write(playbook_content)
            temp_playbook = f.name

        try:
            return self.run_playbook(temp_playbook)
        finally:
            # 清理临时文件
            Path(temp_playbook).unlink()

    def _create_step_playbook(
        self,
        step: HardeningStep,
        target_host: str
    ) -> str:
        """为单个步骤创建 Ansible 剧本 YAML。

        Args:
            step: HardeningStep 对象
            target_host: 目标主机

        Returns:
            YAML 格式的剧本文本

        示例输出:
            ---
            - hosts: localhost
              gather_facts: no
              tasks:
                - name: 禁用 root 登录
                  lineinfile:
                    path: "/etc/ssh/sshd_config"
                    line: "PermitRootLogin no"
        """
        return f"""---
- hosts: {target_host}
  gather_facts: no
  tasks:
    - name: {step.name}
      {step.module}:
        {self._format_params(step.params)}
"""

    def _format_params(self, params: Dict[str, Any]) -> str:
        """将参数字典格式化为 YAML 格式。

        Args:
            params: 参数字典

        Returns:
            YAML 格式的参数字符串

        示例:
            >>> params = {"path": "/etc/test", "mode": "0644"}
            >>> _format_params(params)
            'path: "/etc/test"\n        mode: "0644"'
        """
        lines = []
        for key, value in params.items():
            lines.append(f"{key}: {json.dumps(value)}")
        return "\n        ".join(lines)


def run_playbook(
    playbook_name: str,
    extra_vars: Optional[Dict[str, Any]] = None
) -> ExecutionResult:
    """便捷函数 - 执行单个剧本。

    Args:
        playbook_name: 剧本文件名
        extra_vars: 额外变量字典

    Returns:
        ExecutionResult 对象

    Examples:
        >>> result = run_playbook("ssh_hardening.yml")
        >>> if result.success:
        ...     print(f"执行成功：{result.steps_executed} 步骤")
    """
    runner = AnsibleRunner()
    return runner.run_playbook(playbook_name, extra_vars)


def run_hardening(
    plans: List[HardeningPlan],
    target_host: str = "localhost"
) -> List[ExecutionResult]:
    """执行加固计划列表。

    遍历所有计划的所有步骤并逐个执行。

    Args:
        plans: HardeningPlan 对象列表
        target_host: 目标主机，默认"localhost"

    Returns:
        ExecutionResult 对象列表，每个步骤一个结果

    Examples:
        >>> results = run_hardening(plans)
        >>> successful = sum(1 for r in results if r.success)
        >>> print(f"成功：{successful}/{len(results)}")
    """
    runner = AnsibleRunner()
    results = []

    for plan in plans:
        for step in plan.steps:
            result = runner.run_step(step, target_host)
            result.plan_id = f"{plan.rule_id}_步骤{step.name}"
            results.append(result)

    return results


def execute_hardening_plan(
    plan: HardeningPlan,
    target_host: str = "localhost"
) -> ExecutionResult:
    """执行单个加固计划。

    执行计划中的所有步骤并汇总结果。

    Args:
        plan: HardeningPlan 对象
        target_host: 目标主机，默认"localhost"

    Returns:
        ExecutionResult 对象，包含汇总结果

    汇总逻辑:
        - success: 所有步骤都成功则为 True
        - steps_executed: 成功的步骤数
        - steps_failed: 失败的步骤数
        - output: 所有步骤的输出合并
        - error: 所有步骤的错误合并
    """
    runner = AnsibleRunner()
    results = []

    # 执行所有步骤
    for step in plan.steps:
        result = runner.run_step(step, target_host)
        results.append(result)

    # 统计结果
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    return ExecutionResult(
        plan_id=plan.rule_id,
        success=failed_count == 0,
        steps_executed=success_count,
        steps_failed=failed_count,
        output="\n".join(r.output for r in results),
        error="\n".join(r.error for r in results if r.error)
    )


def get_execution_feedback(result: ExecutionResult) -> Dict[str, Any]:
    """从执行结果生成反馈信息。

    提取执行结果的关键信息用于反馈给代理模块。

    Args:
        result: ExecutionResult 对象

    Returns:
        反馈字典，包含：
        - success: 执行是否成功
        - steps_completed: 完成的步骤数
        - steps_failed: 失败的步骤数
        - error_message: 错误消息
        - timestamp: 执行时间戳

    Examples:
        >>> feedback = get_execution_feedback(result)
        >>> if not feedback["success"]:
        ...     print(f"执行失败：{feedback['error_message']}")
    """
    return {
        "success": result.success,
        "steps_completed": result.steps_executed,
        "steps_failed": result.steps_failed,
        "error_message": result.error,
        "timestamp": result.timestamp
    }
