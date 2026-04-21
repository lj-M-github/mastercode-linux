"""Hierarchical Knowledge Graph Store.

维护知识图谱的完整内存状态：
- 节点索引（node_id → GraphNode）
- 层次索引（level → List[node_id]）
- 有向邻接表（出边 & 入边）
- 序列化 / 反序列化支持（JSON）
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Set

from .graph_node import (
    LEVEL_LABELS,
    GraphEdge,
    GraphNode,
    REL_BELONGS_TO,
    REL_CONTAINS,
)

logger = logging.getLogger(__name__)


class GraphStore:
    """内存层次知识图谱。

    存储结构：
    - ``_nodes``:       node_id → GraphNode
    - ``_out_edges``:   node_id → List[GraphEdge]  （出边）
    - ``_in_edges``:    node_id → List[GraphEdge]  （入边）
    - ``_level_index``: level   → Set[node_id]

    Examples:
        >>> gs = GraphStore()
        >>> fw = GraphNode.make_framework("CIS")
        >>> gs.add_node(fw)
        >>> gs.add_edge(GraphEdge(fw.node_id, dom.node_id, REL_CONTAINS))
        >>> parents = gs.get_ancestors("some/ctrl/id")
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._out_edges: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._in_edges: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._level_index: Dict[int, Set[str]] = defaultdict(set)

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """添加节点（已存在则更新）。"""
        if node.node_id in self._nodes:
            # 仅更新内容和 embedding，保留已有边
            existing = self._nodes[node.node_id]
            if node.content:
                existing.content = node.content
            if node.embedding is not None:
                existing.embedding = node.embedding
            existing.metadata.update(node.metadata)
            return
        self._nodes[node.node_id] = node
        self._level_index[node.level].add(node.node_id)

    def add_nodes(self, nodes: Iterable[GraphNode]) -> int:
        """批量添加节点，返回新增数量。"""
        count = 0
        for n in nodes:
            existed = n.node_id in self._nodes
            self.add_node(n)
            if not existed:
                count += 1
        return count

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def nodes_at_level(self, level: int) -> List[GraphNode]:
        """返回指定层次的所有节点。"""
        return [self._nodes[nid] for nid in self._level_index.get(level, set())]

    def all_nodes(self) -> Iterator[GraphNode]:
        return iter(self._nodes.values())

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def add_edge(self, edge: GraphEdge) -> None:
        """添加有向边（幂等）。"""
        # 去重：同 (source, target, relation) 只保留一条
        existing = self._out_edges[edge.source_id]
        for e in existing:
            if e.target_id == edge.target_id and e.relation == edge.relation:
                return
        self._out_edges[edge.source_id].append(edge)
        self._in_edges[edge.target_id].append(edge)

    def add_hierarchy_edge(self, parent_id: str, child_id: str) -> None:
        """添加双向层级边（CONTAINS + BELONGS_TO）。"""
        self.add_edge(GraphEdge(parent_id, child_id, REL_CONTAINS))
        self.add_edge(GraphEdge(child_id, parent_id, REL_BELONGS_TO))

    def get_children(self, node_id: str) -> List[GraphNode]:
        """返回直接子节点（CONTAINS 关系）。"""
        children = []
        for edge in self._out_edges.get(node_id, []):
            if edge.relation == REL_CONTAINS:
                child = self._nodes.get(edge.target_id)
                if child:
                    children.append(child)
        return children

    def get_parent(self, node_id: str) -> Optional[GraphNode]:
        """返回直接父节点（BELONGS_TO 关系，取第一个）。"""
        for edge in self._out_edges.get(node_id, []):
            if edge.relation == REL_BELONGS_TO:
                return self._nodes.get(edge.target_id)
        return None

    def get_out_edges(self, node_id: str) -> List[GraphEdge]:
        return list(self._out_edges.get(node_id, []))

    def get_in_edges(self, node_id: str) -> List[GraphEdge]:
        return list(self._in_edges.get(node_id, []))

    # ------------------------------------------------------------------
    # Traversal helpers
    # ------------------------------------------------------------------

    def get_ancestors(self, node_id: str) -> List[GraphNode]:
        """沿 BELONGS_TO 边向上遍历，返回从直接父到根的祖先列表。"""
        ancestors: List[GraphNode] = []
        visited: Set[str] = {node_id}
        current_id = node_id
        while True:
            parent = self.get_parent(current_id)
            if parent is None or parent.node_id in visited:
                break
            ancestors.append(parent)
            visited.add(parent.node_id)
            current_id = parent.node_id
        return ancestors

    def get_descendants(
        self, node_id: str, max_depth: int = 3
    ) -> List[GraphNode]:
        """BFS 向下遍历 CONTAINS 边，返回所有后代节点（限深度）。"""
        result: List[GraphNode] = []
        visited: Set[str] = {node_id}
        queue: List[tuple[str, int]] = [(node_id, 0)]
        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for child in self.get_children(current_id):
                if child.node_id not in visited:
                    visited.add(child.node_id)
                    result.append(child)
                    queue.append((child.node_id, depth + 1))
        return result

    def get_related(
        self, node_id: str, relation: Optional[str] = None
    ) -> List[GraphNode]:
        """返回通过指定关系连接的邻居节点（默认所有出边关系）。"""
        nodes = []
        for edge in self._out_edges.get(node_id, []):
            if relation is None or edge.relation == relation:
                n = self._nodes.get(edge.target_id)
                if n:
                    nodes.append(n)
        return nodes

    def get_siblings(self, node_id: str) -> List[GraphNode]:
        """返回与该节点拥有相同父节点的兄弟节点。"""
        parent = self.get_parent(node_id)
        if parent is None:
            return []
        return [c for c in self.get_children(parent.node_id) if c.node_id != node_id]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, int]:
        total_edges = sum(len(v) for v in self._out_edges.values())
        level_counts = {
            LEVEL_LABELS.get(lvl, str(lvl)): len(ids)
            for lvl, ids in self._level_index.items()
        }
        return {
            "total_nodes": len(self._nodes),
            "total_edges": total_edges,
            **level_counts,
        }

    # ------------------------------------------------------------------
    # Persistence (JSON)
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """将图谱序列化为 JSON 文件。"""
        data = {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "level": n.level,
                    "label": n.label,
                    "content": n.content,
                    "metadata": n.metadata,
                    # embedding 不序列化（体积过大，重建时重新编码）
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation": e.relation,
                    "weight": e.weight,
                }
                for edges in self._out_edges.values()
                for e in edges
            ],
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("GraphStore saved: %d nodes, %d edges → %s",
                    len(data["nodes"]), len(data["edges"]), path)

    @classmethod
    def load(cls, path: str) -> "GraphStore":
        """从 JSON 文件加载图谱。"""
        gs = cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for nd in data.get("nodes", []):
            gs.add_node(
                GraphNode(
                    node_id=nd["node_id"],
                    level=nd["level"],
                    label=nd["label"],
                    content=nd["content"],
                    metadata=nd.get("metadata", {}),
                )
            )
        for ed in data.get("edges", []):
            gs.add_edge(
                GraphEdge(
                    source_id=ed["source_id"],
                    target_id=ed["target_id"],
                    relation=ed["relation"],
                    weight=ed.get("weight", 1.0),
                )
            )
        logger.info("GraphStore loaded: %d nodes from %s", len(gs._nodes), path)
        return gs

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes
