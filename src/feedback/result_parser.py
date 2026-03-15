"""Result Parser module - Parse execution results."""

import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExecutionResult:
    """执行结果数据类。

    Attributes:
        task_id: 任务标识
        success: 是否成功
        steps_executed: 执行的步骤数
        steps_failed: 失败的步骤数
        output: 标准输出
        error: 错误输出
        duration: 执行耗时（秒）
        timestamp: 时间戳
    """
    task_id: str
    success: bool
    steps_executed: int = 0
    steps_failed: int = 0
    output: str = ""
    error: str = ""
    duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "steps_executed": self.steps_executed,
            "steps_failed": self.steps_failed,
            "output": self.output,
            "error": self.error,
            "duration": self.duration,
            "timestamp": self.timestamp
        }


class ResultParser:
    """执行结果解析器。

    负责解析 Ansible 执行结果并提取关键信息。

    Examples:
        >>> parser = ResultParser()
        >>> result = parser.parse(ansible_output)
    """

    def parse(self, output: str, task_id: str = "") -> ExecutionResult:
        """解析执行输出。

        Args:
            output: 执行输出
            task_id: 任务标识

        Returns:
            ExecutionResult 对象
        """
        recap = self._extract_recap_values(output)
        success = self._determine_success(output)
        steps_executed = recap["ok"] + recap["changed"]
        steps_failed = recap["failed"] + recap["unreachable"]

        return ExecutionResult(
            task_id=task_id,
            success=success,
            steps_executed=steps_executed,
            steps_failed=steps_failed,
            output=output
        )

    def parse_json(self, json_output: str) -> ExecutionResult:
        """解析 JSON 格式输出。

        Args:
            json_output: JSON 格式输出

        Returns:
            ExecutionResult 对象
        """
        data = json.loads(json_output)

        return ExecutionResult(
            task_id=data.get("task_id", ""),
            success=data.get("success", False),
            steps_executed=data.get("steps_executed", 0),
            steps_failed=data.get("steps_failed", 0),
            output=data.get("output", ""),
            error=data.get("error", ""),
            duration=data.get("duration", 0.0)
        )

    def _determine_success(self, output: str) -> bool:
        """判断执行是否成功。

        Args:
            output: 执行输出

        Returns:
            是否成功
        """
        recap = self._extract_recap_values(output)
        has_recap = any(v > 0 for v in recap.values())

        # 正常情况下优先信任 recap 数值
        if has_recap:
            return (recap["failed"] + recap["unreachable"]) == 0

        # 无 recap 时，回退到关键失败信号判断，避免误判成功
        output_lower = output.lower()
        failure_signals = [
            "failed!",
            "fatal:",
            "unreachable",
            "permission denied",
            "traceback",
            "exception"
        ]
        return not any(signal in output_lower for signal in failure_signals)

    def _extract_recap_values(self, text: str) -> Dict[str, int]:
        """从 Ansible 输出中提取聚合的 recap 值。

        支持如下模式：
        ok=3 changed=2 unreachable=0 failed=1

        Args:
            text: Ansible 输出文本

        Returns:
            包含 ok, changed, failed, unreachable 的字典
        """
        values = {
            "ok": 0,
            "changed": 0,
            "failed": 0,
            "unreachable": 0,
        }

        for key, value in re.findall(r"(ok|changed|failed|unreachable)=(\d+)", text):
            values[key] += int(value)

        return values

    def _count_pattern(self, text: str, patterns: List[str]) -> int:
        """统计模式出现次数。

        Args:
            text: 文本
            patterns: 模式列表

        Returns:
            总次数
        """
        count = 0
        for pattern in patterns:
            count += text.count(pattern)
        return count

    def get_feedback_dict(self, result: ExecutionResult) -> Dict[str, Any]:
        """生成反馈字典。

        Args:
            result: 执行结果

        Returns:
            反馈字典
        """
        return {
            "success": result.success,
            "steps_completed": result.steps_executed,
            "steps_failed": result.steps_failed,
            "error_message": result.error,
            "timestamp": result.timestamp
        }
