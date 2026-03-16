"""Prompt Templates module - Reusable prompt templates."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class SystemPrompt:
    """系统提示词数据类。

    Attributes:
        role: 角色描述
        constraints: 约束条件列表
        output_format: 输出格式要求
    """
    role: str
    constraints: List[str] = field(default_factory=list)
    output_format: str = ""

    def build(self) -> str:
        """构建系统提示词。

        Returns:
            完整的系统提示词
        """
        parts = [self.role]

        if self.constraints:
            parts.append("\n\n## Constraints")
            for constraint in self.constraints:
                parts.append(f"- {constraint}")

        if self.output_format:
            parts.append(f"\n\n## Output Format\n{self.output_format}")

        return "".join(parts)


class PromptTemplate:
    """提示词模板。

    支持变量替换的模板系统。

    Attributes:
        template: 模板字符串
        variables: 变量列表

    Examples:
        >>> template = PromptTemplate("Hello, {name}!")
        >>> prompt = template.format(name="World")
        >>> print(prompt)
        'Hello, World!'
    """

    def __init__(self, template: str):
        """初始化模板。

        Args:
            template: 模板字符串
        """
        self.template = template
        self.variables = self._extract_variables()

    def _extract_variables(self) -> List[str]:
        """提取模板中的变量。

        Returns:
            变量名列表
        """
        import re
        return re.findall(r'\{(\w+)\}', self.template)

    def format(self, **kwargs: Any) -> str:
        """格式化模板。

        Args:
            **kwargs: 变量值

        Returns:
            格式化后的提示词
        """
        return self.template.format(**kwargs)

    def validate(self, **kwargs: Any) -> bool:
        """验证变量是否完整。

        Args:
            **kwargs: 变量值

        Returns:
            是否所有变量都已提供
        """
        return all(var in kwargs for var in self.variables)


# ==================== 预定义模板 ====================

SECURITY_REMEDIATION_TEMPLATE = PromptTemplate(
    """请将以下安全规则转换为 Ansible tasks：

**规则编号**: {rule_id}
**规则标题**: {section_title}
**云厂商**: {cloud_provider}
**修复建议**:
{remediation}

请输出 YAML 格式的 Ansible tasks："""
)

CODE_GENERATION_SYSTEM_PROMPT = SystemPrompt(
    role="你是一个专业的云安全加固和 Ansible 自动化专家。"
    "你的任务是将云安全基准文档中的安全规则转换为可执行的 Ansible Playbook。",
    constraints=[
        "输出必须是合法的 YAML 格式",
        "只输出 Ansible task，不要包含解释性文字",
        "每个 task 必须包含 name 和对应的 Ansible 模块",
        "如果规则不适用或信息不足，返回空列表"
    ],
    output_format="""```yaml
- name: [任务描述]
  [module_name]:
    [parameters]
```"""
)

ERROR_ANALYSIS_TEMPLATE = PromptTemplate(
    """分析以下 Ansible 执行错误并提供修复建议：

**错误信息**:
{error_message}

**原始 Playbook**:
{playbook_content}

请提供：
1. 错误原因分析
2. 修复建议
3. 修正后的 Playbook"""
)

SELF_HEALING_TEMPLATE = PromptTemplate(
    """根据以下执行错误，重新生成修复后的 Playbook：

**失败原因**: {failure_reason}
**原始规则**: {original_rule}
**执行日志**: {execution_log}

请生成修正后的 Ansible Playbook："""
)
