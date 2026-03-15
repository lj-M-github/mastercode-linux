"""Playbook Builder module - Build Ansible playbooks programmatically."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class Task:
    """Ansible Task 数据类。

    Attributes:
        name: 任务名称
        module: 模块名
        params: 模块参数
        when: 条件
        register: 注册变量
    """
    name: str
    module: str
    params: Dict[str, Any] = field(default_factory=dict)
    when: str = ""
    register: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        task_dict = {
            "name": self.name,
            self.module: self.params
        }
        if self.when:
            task_dict["when"] = self.when
        if self.register:
            task_dict["register"] = self.register
        return task_dict


class PlaybookBuilder:
    """Playbook 构建器。

    负责 programmatically 构建 Ansible Playbook。

    Attributes:
        name: Playbook 名称
        hosts: 目标主机
        become: 是否提权
        gather_facts: 是否收集事实
        tasks: 任务列表

    Examples:
        >>> builder = PlaybookBuilder("SSH Hardening", "all")
        >>> builder.add_task("Disable root login", "lineinfile", {...})
        >>> playbook = builder.build()
    """

    def __init__(
        self,
        name: str,
        hosts: str = "all",
        become: bool = True,
        gather_facts: bool = True
    ):
        """初始化 Playbook 构建器。

        Args:
            name: Playbook 名称
            hosts: 目标主机
            become: 是否提权
            gather_facts: 是否收集事实
        """
        self.name = name
        self.hosts = hosts
        self.become = become
        self.gather_facts = gather_facts
        self.tasks: List[Task] = []

    def add_task(
        self,
        name: str,
        module: str,
        params: Optional[Dict[str, Any]] = None,
        when: str = "",
        register: str = ""
    ) -> "PlaybookBuilder":
        """添加任务。

        Args:
            name: 任务名称
            module: 模块名
            params: 模块参数
            when: 条件
            register: 注册变量

        Returns:
            self（支持链式调用）
        """
        task = Task(
            name=name,
            module=module,
            params=params or {},
            when=when,
            register=register
        )
        self.tasks.append(task)
        return self

    def build(self) -> str:
        """构建 Playbook。

        Returns:
            YAML 格式 Playbook
        """
        play = {
            "name": self.name,
            "hosts": self.hosts,
            "become": self.become,
            "gather_facts": self.gather_facts,
            "tasks": [task.to_dict() for task in self.tasks]
        }

        return yaml.dump([play], default_flow_style=False, sort_keys=False)

    def save(self, filepath: str) -> str:
        """保存 Playbook到文件。

        Args:
            filepath: 文件路径

        Returns:
            保存的路径
        """
        content = self.build()
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(path)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "PlaybookBuilder":
        """从 YAML 创建构建器。

        Args:
            yaml_content: YAML 内容

        Returns:
            PlaybookBuilder 实例
        """
        data = yaml.safe_load(yaml_content)
        if isinstance(data, list):
            data = data[0]

        builder = cls(
            name=data.get("name", "Playbook"),
            hosts=data.get("hosts", "all"),
            become=data.get("become", True),
            gather_facts=data.get("gather_facts", True)
        )

        for task_data in data.get("tasks", []):
            if not isinstance(task_data, dict):
                continue

            name = task_data.get("name", "")
            # 识别模块
            for key, value in task_data.items():
                if key not in ["name", "when", "register", "tags"]:
                    builder.add_task(
                        name=name,
                        module=key,
                        params=value if isinstance(value, dict) else {},
                        when=task_data.get("when", ""),
                        register=task_data.get("register", "")
                    )
                    break

        return builder
