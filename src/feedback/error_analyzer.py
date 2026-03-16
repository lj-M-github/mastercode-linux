"""Error Analyzer module - Analyze execution errors."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from llm.llm_client import LLMClient
from llm.prompt_templates import PromptTemplate, ERROR_ANALYSIS_TEMPLATE


@dataclass
class ErrorAnalysis:
    """错误分析结果数据类。

    Attributes:
        error_type: 错误类型
        error_message: 错误消息
        root_cause: 根本原因
        suggestion: 修复建议
        severity: 严重程度
    """
    error_type: str
    error_message: str
    root_cause: str
    suggestion: str
    severity: str  # low, medium, high, critical


class ErrorAnalyzer:
    """错误分析器。

    负责分析执行错误并提供修复建议。

    Attributes:
        llm_client: LLM 客户端

    Examples:
        >>> analyzer = ErrorAnalyzer(llm_client)
        >>> analysis = analyzer.analyze(error_message, playbook)
    """

    ERROR_TYPES = {
        "syntax": ["syntax error", "yaml error", "parse error"],
        "connection": ["connection failed", "unreachable", "timeout"],
        "permission": ["permission denied", "access denied", "unauthorized"],
        "command": ["command not found", "no such file", "missing"],
        "logic": ["failed", "error", "exception"]
    }

    SEVERITY_LEVELS = {
        "syntax": "high",
        "connection": "medium",
        "permission": "high",
        "command": "medium",
        "logic": "low"
    }

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """初始化错误分析器。

        Args:
            llm_client: LLM 客户端
        """
        self.llm_client = llm_client

    def analyze(
        self,
        error_message: str,
        playbook_content: str = ""
    ) -> ErrorAnalysis:
        """分析错误。

        Args:
            error_message: 错误消息
            playbook_content: Playbook 内容

        Returns:
            ErrorAnalysis 对象
        """
        error_type = self._classify_error(error_message)
        severity = self.SEVERITY_LEVELS.get(error_type, "medium")

        # 使用 LLM 进行深入分析
        if self.llm_client and playbook_content:
            analysis = self._llm_analyze(error_message, playbook_content)
            root_cause = analysis.get("root_cause", "Unknown")
            suggestion = analysis.get("suggestion", "Please check the error and try again.")
        else:
            root_cause = self._get_common_cause(error_type, error_message)
            suggestion = self._get_suggestion(error_type)

        return ErrorAnalysis(
            error_type=error_type,
            error_message=error_message,
            root_cause=root_cause,
            suggestion=suggestion,
            severity=severity
        )

    def _classify_error(self, error_message: str) -> str:
        """分类错误类型。

        Args:
            error_message: 错误消息

        Returns:
            错误类型
        """
        error_lower = error_message.lower()

        for error_type, keywords in self.ERROR_TYPES.items():
            for keyword in keywords:
                if keyword in error_lower:
                    return error_type

        return "logic"

    def _get_common_cause(self, error_type: str, error_message: str) -> str:
        """获取常见原因。

        Args:
            error_type: 错误类型
            error_message: 错误消息

        Returns:
            可能的原因
        """
        causes = {
            "syntax": "YAML 语法错误或格式不正确",
            "connection": "网络连接问题或目标主机不可达",
            "permission": "权限不足或认证失败",
            "command": "命令或文件不存在",
            "logic": "执行逻辑错误"
        }
        return causes.get(error_type, "未知错误")

    def _get_suggestion(self, error_type: str) -> str:
        """获取修复建议。

        Args:
            error_type: 错误类型

        Returns:
            修复建议
        """
        suggestions = {
            "syntax": "检查 YAML 缩进和语法格式",
            "connection": "检查网络连接和目标主机状态",
            "permission": "验证凭证和权限设置",
            "command": "确认命令路径和依赖已安装",
            "logic": "检查 Playbook 逻辑和参数"
        }
        return suggestions.get(error_type, "请检查错误日志")

    def _llm_analyze(
        self,
        error_message: str,
        playbook_content: str
    ) -> Dict[str, str]:
        """使用 LLM 分析错误。

        Args:
            error_message: 错误消息
            playbook_content: Playbook 内容

        Returns:
            分析结果字典
        """
        prompt = ERROR_ANALYSIS_TEMPLATE.format(
            error_message=error_message,
            playbook_content=playbook_content
        )

        response = self.llm_client.generate(prompt)
        content = response.content

        # 简单解析响应
        return {
            "root_cause": self._extract_section(content, "错误原因") or content[:200],
            "suggestion": self._extract_section(content, "修复建议") or content
        }

    def _extract_section(self, text: str, section_name: str) -> str:
        """提取文本中的章节内容。

        Args:
            text: 文本
            section_name: 章节名

        Returns:
            章节内容
        """
        import re
        pattern = rf"{section_name}[:：]?\s*(.+?)(?=\n\d+\.|\n##|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def batch_analyze(
        self,
        errors: List[Dict[str, str]]
    ) -> List[ErrorAnalysis]:
        """批量分析错误。

        Args:
            errors: 错误列表，每项包含 error_message 和 playbook_content

        Returns:
            ErrorAnalysis 对象列表
        """
        return [
            self.analyze(
                error.get("error_message", ""),
                error.get("playbook_content", "")
            )
            for error in errors
        ]
