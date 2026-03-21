"""Self Heal module - Automatic error recovery and playbook rewriting."""

from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

from ..llm.llm_client import LLMClient
from ..llm.prompt_templates import PromptTemplate, SELF_HEALING_TEMPLATE
from ..utils.yaml_utils import extract_yaml
from .error_analyzer import ErrorAnalyzer, ErrorAnalysis


@dataclass
class HealingResult:
    """自愈结果数据类。

    Attributes:
        success: 是否成功
        rewritten_playbook: 重写的 Playbook
        attempts: 尝试次数
        execution_result: 执行结果
        error_history: 错误历史
    """
    success: bool
    rewritten_playbook: str = ""
    attempts: int = 0
    execution_result: Any = None
    error_history: List[str] = field(default_factory=list)


class SelfHealer:
    """自愈模块。

    负责根据执行错误自动修复 Playbook 并重试。

    Attributes:
        llm_client: LLM 客户端
        error_analyzer: 错误分析器
        max_retries: 最大重试次数

    Examples:
        >>> healer = SelfHealer(llm_client, max_retries=3)
        >>> result = healer.heal(original_playbook, error_log)
    """

    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_retries: int = DEFAULT_MAX_RETRIES
    ):
        """初始化自愈器。

        Args:
            llm_client: LLM 客户端
            max_retries: 最大重试次数
        """
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.error_analyzer = ErrorAnalyzer(llm_client)

    def heal(
        self,
        original_playbook: str,
        error_log: str,
        original_rule: str = "",
        execute_fn: Optional[Callable[[str], Any]] = None
    ) -> HealingResult:
        """执行自愈。

        Args:
            original_playbook: 原始 Playbook
            error_log: 错误日志
            original_rule: 原始规则
            execute_fn: 执行回调函数，用于实际执行修复后的 Playbook

        Returns:
            HealingResult 对象
        """
        if not self.llm_client:
            return HealingResult(
                success=False,
                error_history=["No LLM client available"]
            )

        error_history = []
        current_playbook = original_playbook
        attempted_rewrites = 0
        last_execution_result = None

        for attempt in range(1, self.max_retries + 1):
            # 对不可重试错误立即停止，避免无意义重试
            if not self.can_retry(error_log):
                error_history.append(f"Attempt {attempt}: non-retryable error")
                break

            # 分析当前错误
            attempted_rewrites += 1
            analysis = self.error_analyzer.analyze(error_log, current_playbook)
            error_history.append(f"Attempt {attempt}: {analysis.error_message}")

            # 生成修复后的 Playbook
            rewritten = self._rewrite_playbook(
                current_playbook,
                analysis.root_cause,
                error_log,
                original_rule
            )

            if not rewritten:
                continue

            current_playbook = rewritten

            # 优先使用真实执行结果（如果提供了回调）
            if execute_fn is not None:
                retry_result = execute_fn(current_playbook)
                last_execution_result = retry_result  # 记录最后一次执行结果
                if getattr(retry_result, "success", False):
                    return HealingResult(
                        success=True,
                        rewritten_playbook=current_playbook,
                        attempts=attempted_rewrites,
                        execution_result=retry_result,
                        error_history=error_history
                    )
                # 更新下一轮错误输入，而不是复用旧的错误
                retry_error = getattr(retry_result, "error", "") or getattr(retry_result, "output", "")
                if retry_error:
                    error_log = retry_error
                continue

            # 向后兼容路径（无回调）
            import warnings
            warnings.warn(
                "heal() 未提供 execute_fn，将使用静态分析判断修复结果，建议传入 execute_fn 以获得可靠的自愈效果",
                DeprecationWarning,
                stacklevel=2
            )
            if self._is_fixed(analysis):
                return HealingResult(
                    success=True,
                    rewritten_playbook=current_playbook,
                    attempts=attempted_rewrites,
                    error_history=error_history
                )

        # 达到最大重试次数
        return HealingResult(
            success=False,
            rewritten_playbook=current_playbook,
            attempts=attempted_rewrites,
            error_history=error_history,
            execution_result=last_execution_result
        )

    def _rewrite_playbook(
        self,
        playbook: str,
        failure_reason: str,
        execution_log: str,
        original_rule: str
    ) -> str:
        """重写 Playbook。

        Args:
            playbook: 原始 Playbook
            failure_reason: 失败原因
            execution_log: 执行日志/错误日志
            original_rule: 原始规则

        Returns:
            重写的 Playbook
        """
        if not self.llm_client:
            return playbook

        prompt = SELF_HEALING_TEMPLATE.format(
            failure_reason=failure_reason,
            original_rule=original_rule,
            execution_log=execution_log
        )

        response = self.llm_client.generate(prompt, task_type="error_analysis")

        # 提取 YAML 代码块
        rewritten = extract_yaml(response.content)
        return rewritten or playbook

    def _is_fixed(self, analysis: ErrorAnalysis) -> bool:
        """判断是否已修复。

        Args:
            analysis: 错误分析

        Returns:
            是否已修复
        """
        # 基于错误类型判断
        fixed_keywords = ["fixed", "resolved", "corrected", "已修复", "已解决"]
        suggestion_lower = analysis.suggestion.lower()

        return any(keyword in suggestion_lower for keyword in fixed_keywords)

    def can_retry(self, error: str) -> bool:
        """判断是否可以重试。

        权限错误可以通过 become: yes 修复，属于可重试。
        只有真正的认证失败才是不可重试的。
        """
        # 只有真正的认证失败不可重试
        non_retryable = [
            "invalid credentials",
            "authentication failed",
            # 注意：permission denied 可通过 become: yes 修复，属于可重试
        ]

        error_lower = error.lower()
        return not any(keyword in error_lower for keyword in non_retryable)

    def get_healing_stats(self, results: List[HealingResult]) -> Dict[str, Any]:
        """获取自愈统计。

        Args:
            results: 自愈结果列表

        Returns:
            统计信息
        """
        success_count = sum(1 for r in results if r.success)

        return {
            "total_attempts": len(results),
            "successful_healings": success_count,
            "failed_healings": len(results) - success_count,
            "success_rate": success_count / len(results) if results else 0,
            "avg_attempts": sum(r.attempts for r in results) / len(results) if results else 0
        }
