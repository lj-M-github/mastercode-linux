"""YAML 工具模块 - 提供通用的 YAML 处理功能。"""

import re
from typing import Optional


def extract_yaml(text: str) -> Optional[str]:
    """从文本中提取 YAML 内容。

    尝试从 LLM 响应中提取 YAML 代码块，支持多种格式：
    - ```yaml ... ``` 代码块
    - ``` ... ``` 代码块
    - 直接以 --- 或 - name: 等开头的 YAML 内容

    Args:
        text: 包含 YAML 的文本

    Returns:
        提取的 YAML 内容，如果未找到则返回 None

    Examples:
        >>> text = "Here is the playbook:\\n```yaml\\n---\\n- hosts: all\\n```"
        >>> extract_yaml(text)
        '---\\n- hosts: all'
    """
    yaml_match = re.search(r'```(?:yaml)?\s*(.*?)```', text, re.DOTALL)
    if yaml_match:
        return yaml_match.group(1).strip()

    stripped = text.strip()
    if looks_like_yaml(stripped):
        return stripped

    for marker in ("---", "- name:", "- hosts:"):
        index = stripped.find(marker)
        if index != -1:
            candidate = stripped[index:].strip()
            if looks_like_yaml(candidate):
                return candidate

    return None


def looks_like_yaml(text: str) -> bool:
    """判断文本是否看起来像可执行的 playbook/yaml。

    通过检查常见的 Ansible playbook 关键词来判断。

    Args:
        text: 待判断的文本

    Returns:
        是否看起来像 YAML/Playbook

    Examples:
        >>> looks_like_yaml("- hosts: all\\n  tasks:")
        True
        >>> looks_like_yaml("This is not YAML")
        False
    """
    if not text:
        return False

    yaml_indicators = ["hosts:", "tasks:", "- name:", "gather_facts:", "become:"]
    return any(indicator in text for indicator in yaml_indicators)
