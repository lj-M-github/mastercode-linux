"""Knowledge Graph Node and Edge definitions.

层次结构（Level）：
  0  FRAMEWORK  —— CIS / NIST / STIG 框架顶层
  1  DOMAIN     —— 安全域（Access Control / Network / Kernel …）
  2  CATEGORY   —— 类别（SSH / Firewall / Users …）
  3  CONTROL    —— 具体安全控制项
  4  DETAIL     —— 实施细节 / 修复步骤 / 审计依据
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Level constants
# ---------------------------------------------------------------------------

LEVEL_FRAMEWORK = 0
LEVEL_DOMAIN = 1
LEVEL_CATEGORY = 2
LEVEL_CONTROL = 3
LEVEL_DETAIL = 4

LEVEL_LABELS = {
    LEVEL_FRAMEWORK: "FRAMEWORK",
    LEVEL_DOMAIN: "DOMAIN",
    LEVEL_CATEGORY: "CATEGORY",
    LEVEL_CONTROL: "CONTROL",
    LEVEL_DETAIL: "DETAIL",
}

# ---------------------------------------------------------------------------
# Edge relation types
# ---------------------------------------------------------------------------

REL_CONTAINS = "CONTAINS"       # 父 → 子（层级包含）
REL_BELONGS_TO = "BELONGS_TO"   # 子 → 父（层级归属）
REL_RELATED_TO = "RELATED_TO"   # 同级或跨级语义关联
REL_IMPLEMENTS = "IMPLEMENTS"   # DETAIL → CONTROL
REL_REQUIRES = "REQUIRES"       # CONTROL → CONTROL 依赖


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GraphNode:
    """知识图谱节点。

    Attributes:
        node_id:   唯一标识，格式建议 ``<framework>/<domain>/<category>/<ctrl_id>``
        level:     层次深度（0–4）
        label:     层次名称（FRAMEWORK / DOMAIN / CATEGORY / CONTROL / DETAIL）
        content:   节点的主要文本内容
        metadata:  附加结构化属性（framework, domain, category, control_id …）
        embedding: 句向量（可选，延迟填充）
    """

    node_id: str
    level: int
    label: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @classmethod
    def make_framework(cls, framework: str, content: str = "") -> "GraphNode":
        node_id = f"fw/{framework.lower()}"
        return cls(
            node_id=node_id,
            level=LEVEL_FRAMEWORK,
            label=LEVEL_LABELS[LEVEL_FRAMEWORK],
            content=content or f"Security framework: {framework}",
            metadata={"framework": framework},
        )

    @classmethod
    def make_domain(cls, framework: str, domain: str, content: str = "") -> "GraphNode":
        node_id = f"fw/{framework.lower()}/domain/{_slug(domain)}"
        return cls(
            node_id=node_id,
            level=LEVEL_DOMAIN,
            label=LEVEL_LABELS[LEVEL_DOMAIN],
            content=content or f"{framework} domain: {domain}",
            metadata={"framework": framework, "domain": domain},
        )

    @classmethod
    def make_category(
        cls, framework: str, domain: str, category: str, content: str = ""
    ) -> "GraphNode":
        node_id = f"fw/{framework.lower()}/domain/{_slug(domain)}/cat/{_slug(category)}"
        return cls(
            node_id=node_id,
            level=LEVEL_CATEGORY,
            label=LEVEL_LABELS[LEVEL_CATEGORY],
            content=content or f"{framework} category: {category}",
            metadata={"framework": framework, "domain": domain, "category": category},
        )

    @classmethod
    def make_control(
        cls,
        framework: str,
        domain: str,
        category: str,
        control_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphNode":
        node_id = f"fw/{framework.lower()}/ctrl/{control_id}"
        meta = {
            "framework": framework,
            "domain": domain,
            "category": category,
            "control_id": control_id,
        }
        if metadata:
            meta.update(metadata)
        return cls(
            node_id=node_id,
            level=LEVEL_CONTROL,
            label=LEVEL_LABELS[LEVEL_CONTROL],
            content=content,
            metadata=meta,
        )

    @classmethod
    def make_detail(
        cls,
        control_node_id: str,
        detail_index: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphNode":
        node_id = f"{control_node_id}/detail/{detail_index}"
        meta = dict(metadata or {})
        meta["parent_control"] = control_node_id
        return cls(
            node_id=node_id,
            level=LEVEL_DETAIL,
            label=LEVEL_LABELS[LEVEL_DETAIL],
            content=content,
            metadata=meta,
        )

    # ------------------------------------------------------------------

    def short_id(self) -> str:
        """返回最后一段 / 分隔的 ID，便于日志显示。"""
        return self.node_id.rsplit("/", 1)[-1]

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GraphNode):
            return self.node_id == other.node_id
        return NotImplemented


@dataclass
class GraphEdge:
    """知识图谱有向边。

    Attributes:
        source_id: 源节点 ID
        target_id: 目标节点 ID
        relation:  关系类型（REL_* 常量）
        weight:    边权重（0–1），用于图检索时的路径衰减
    """

    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0

    def __hash__(self) -> int:
        return hash((self.source_id, self.target_id, self.relation))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GraphEdge):
            return (
                self.source_id == other.source_id
                and self.target_id == other.target_id
                and self.relation == other.relation
            )
        return NotImplemented


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    """将任意字符串转换为安全的路径片段。"""
    return (
        text.lower()
        .replace(" ", "_")
        .replace("/", "-")
        .replace("\\", "-")
    )
