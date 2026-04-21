"""Hierarchical Knowledge Graph Retriever.

混合检索策略（向量检索 + 图遍历）：

1. **向量搜索**（Seed 阶段）
   用 ChromaDB 语义搜索找到最相关的 CONTROL / DETAIL 种子节点。

2. **图扩展**（Context 阶段）
   - 向上遍历祖先链（BELONGS_TO）→ 携带框架/域/类别上下文
   - 同级横向展开（siblings）→ 同一类别内的相关控制项
   - 向下展开直接子节点（CONTAINS）→ 实施细节

3. **评分融合**
   final_score = α × vector_score + β × graph_score + γ × level_weight
   其中：
     vector_score  = ChromaDB 余弦相似度（0–1）
     graph_score   = 图跳数衰减：1 / (1 + hop_distance)
     level_weight  = 优先 CONTROL 节点（level=3），其次 DETAIL（level=4）

4. **去重 & 排序**
   按 final_score 降序返回，去除重复 node_id。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .graph_node import (
    LEVEL_CONTROL,
    LEVEL_DETAIL,
    LEVEL_DOMAIN,
    LEVEL_FRAMEWORK,
    GraphNode,
)
from .graph_store import GraphStore
from ..vector_db.chroma_client import ChromaClient
from ..vector_db.embedding import EmbeddingModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result data class
# ---------------------------------------------------------------------------

@dataclass
class GraphRetrievalResult:
    """图检索结果。

    Attributes:
        node:         对应的图节点
        content:      文本内容（= node.content）
        metadata:     结构化元数据
        vector_score: 向量相似度分数（0–1，-1 表示未参与向量搜索）
        graph_score:  图遍历分数（0–1）
        final_score:  综合评分
        rank:         全局排名（1-based）
        context_path: 层次路径，如 CIS / Network / Firewall / ctrl_1.3.2
        hop_distance: 距种子节点的图跳数（0 = 种子节点本身）
    """

    node: GraphNode
    content: str
    metadata: Dict[str, Any]
    vector_score: float = 0.0
    graph_score: float = 0.0
    final_score: float = 0.0
    rank: int = 0
    context_path: str = ""
    hop_distance: int = 0

    # Convenience
    @property
    def node_id(self) -> str:
        return self.node.node_id

    @property
    def level(self) -> int:
        return self.node.level


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class GraphRetriever:
    """层次知识图谱混合检索器。

    Args:
        graph_store:     GraphStore 实例
        chroma_client:   ChromaDB 客户端（用于种子向量搜索）
        embedding_model: 嵌入模型
        alpha:           向量分数权重（默认 0.6）
        beta:            图跳数分数权重（默认 0.3）
        gamma:           层次权重（默认 0.1）

    Examples:
        >>> gr = GraphRetriever(graph_store, chroma_client, embedding_model)
        >>> results = gr.search("SSH root login should be disabled", n_results=8)
        >>> for r in results:
        ...     print(r.context_path, r.final_score)
    """

    # 层次权重（CONTROL 最高，FRAMEWORK 最低）
    _LEVEL_WEIGHTS = {
        0: 0.3,   # FRAMEWORK
        1: 0.5,   # DOMAIN
        2: 0.6,   # CATEGORY
        3: 1.0,   # CONTROL
        4: 0.8,   # DETAIL
    }

    def __init__(
        self,
        graph_store: GraphStore,
        chroma_client: ChromaClient,
        embedding_model: EmbeddingModel,
        alpha: float = 0.6,
        beta: float = 0.3,
        gamma: float = 0.1,
    ) -> None:
        self.graph_store = graph_store
        self.chroma_client = chroma_client
        self.embedding_model = embedding_model
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        n_results: int = 8,
        seed_k: int = 5,
        expand_siblings: bool = True,
        expand_children: bool = True,
        expand_ancestors: bool = True,
        filter_level: Optional[int] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[GraphRetrievalResult]:
        """混合搜索。

        Args:
            query:            查询文本
            n_results:        返回结果总数
            seed_k:           向量搜索初始种子数
            expand_siblings:  是否扩展同级兄弟节点
            expand_children:  是否扩展子节点（DETAIL）
            expand_ancestors: 是否扩展祖先节点（上下文）
            filter_level:     只返回指定层次的节点
            filter_dict:      ChromaDB metadata 过滤条件

        Returns:
            按 final_score 降序排列的 GraphRetrievalResult 列表
        """
        query_embedding = self.embedding_model.encode_single(query)

        # --- Phase 1: 向量种子搜索 ---
        seed_results = self._vector_search(query_embedding, seed_k, filter_dict)

        # --- Phase 2: 图扩展 ---
        candidates: Dict[str, Tuple[GraphRetrievalResult, int]] = {}  # node_id → (result, hop)

        for vec_result in seed_results:
            node_id = vec_result.node_id
            if node_id in candidates:
                # 已存在：仅提升 vector_score
                candidates[node_id][0].vector_score = max(
                    candidates[node_id][0].vector_score, vec_result.vector_score
                )
                continue
            candidates[node_id] = (vec_result, 0)

            seed_node = vec_result.node

            if expand_ancestors:
                for ancestor in self.graph_store.get_ancestors(node_id):
                    self._add_candidate(
                        candidates, ancestor,
                        hop=len(self.graph_store.get_ancestors(node_id)),
                        vector_score=vec_result.vector_score * 0.4,  # 祖先衰减
                    )

            if expand_siblings:
                for sibling in self.graph_store.get_siblings(node_id):
                    self._add_candidate(
                        candidates, sibling,
                        hop=2,
                        vector_score=vec_result.vector_score * 0.65,
                    )

            if expand_children and seed_node.level <= LEVEL_CONTROL:
                for child in self.graph_store.get_children(node_id):
                    self._add_candidate(
                        candidates, child,
                        hop=1,
                        vector_score=vec_result.vector_score * 0.75,
                    )

        # --- Phase 3: 评分融合 ---
        results = []
        for result, hop in candidates.values():
            result.graph_score = 1.0 / (1.0 + hop)
            lw = self._LEVEL_WEIGHTS.get(result.level, 0.5)
            result.hop_distance = hop
            result.final_score = (
                self.alpha * result.vector_score
                + self.beta * result.graph_score
                + self.gamma * lw
            )
            result.context_path = self._build_context_path(result.node)

            if filter_level is None or result.level == filter_level:
                results.append(result)

        # --- Phase 4: 排序 & 截断 ---
        results.sort(key=lambda r: r.final_score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results[:n_results]

    def search_by_path(
        self,
        framework: Optional[str] = None,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        n_results: int = 20,
    ) -> List[GraphRetrievalResult]:
        """按层次路径过滤返回节点（无向量搜索，纯图遍历）。

        可用于枚举某框架/域/类别下的全部控制项。
        """
        results = []

        for node in self.graph_store.all_nodes():
            m = node.metadata
            if framework and m.get("framework", "").upper() != framework.upper():
                continue
            if domain and m.get("domain", "").lower() != domain.lower():
                continue
            if category and m.get("category", "").lower() != category.lower():
                continue
            results.append(
                GraphRetrievalResult(
                    node=node,
                    content=node.content,
                    metadata=node.metadata,
                    vector_score=0.0,
                    graph_score=1.0,
                    final_score=self._LEVEL_WEIGHTS.get(node.level, 0.5),
                    context_path=self._build_context_path(node),
                )
            )

        results.sort(key=lambda r: (r.level, r.metadata.get("control_id", "")))
        for i, r in enumerate(results):
            r.rank = i + 1
        return results[:n_results]

    def get_context_window(
        self,
        node_id: str,
        include_ancestors: bool = True,
        include_siblings: bool = True,
        include_children: bool = True,
    ) -> Dict[str, Any]:
        """以指定节点为中心，返回完整层次上下文窗口（字典形式）。

        返回结构::

            {
              "node":       {...},
              "ancestors":  [{...}, ...],   # 从父到根
              "siblings":   [{...}, ...],
              "children":   [{...}, ...],
            }
        """
        node = self.graph_store.get_node(node_id)
        if node is None:
            return {}

        def _fmt(n: GraphNode) -> Dict[str, Any]:
            return {
                "node_id": n.node_id,
                "level": n.level,
                "label": n.label,
                "content": n.content[:500],  # 截断防过长
                "metadata": n.metadata,
            }

        return {
            "node": _fmt(node),
            "ancestors": (
                [_fmt(a) for a in self.graph_store.get_ancestors(node_id)]
                if include_ancestors else []
            ),
            "siblings": (
                [_fmt(s) for s in self.graph_store.get_siblings(node_id)]
                if include_siblings else []
            ),
            "children": (
                [_fmt(c) for c in self.graph_store.get_children(node_id)]
                if include_children else []
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _vector_search(
        self,
        query_embedding: List[float],
        k: int,
        filter_dict: Optional[Dict[str, Any]],
    ) -> List[GraphRetrievalResult]:
        """执行向量搜索，将 ChromaDB 结果映射为图节点。"""
        try:
            raw = self.chroma_client.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=filter_dict,
            )
        except Exception as exc:
            logger.warning("ChromaDB query failed: %s", exc)
            return []

        results = []
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            score = max(0.0, 1.0 - dist)

            # 优先通过 node_id 或 control_id 查找图节点
            item_id = meta.get("id", "")
            node = self._resolve_node(item_id, meta, doc)

            if node is None:
                # 节点尚未入图（图和向量库不同步），跳过
                logger.debug("Vector result not in graph: %s", item_id)
                continue

            results.append(
                GraphRetrievalResult(
                    node=node,
                    content=doc,
                    metadata=meta,
                    vector_score=score,
                )
            )

        return results

    def _resolve_node(
        self,
        item_id: str,
        meta: Dict[str, Any],
        content: str,
    ) -> Optional[GraphNode]:
        """尝试定位图中对应向量文档的节点。"""
        # 直接用 ChromaDB item id 查找
        if self.graph_store.has_node(item_id):
            return self.graph_store.get_node(item_id)

        # 通过规范化控制项路径查找
        fw = meta.get("framework", "")
        ctrl_id = meta.get("control_id", "")
        if fw and ctrl_id:
            candidate = f"fw/{fw.lower()}/ctrl/{ctrl_id}"
            if self.graph_store.has_node(candidate):
                return self.graph_store.get_node(candidate)

        # 找不到则返回 None（不创建幽灵节点）
        return None

    def _add_candidate(
        self,
        candidates: Dict[str, Any],
        node: GraphNode,
        hop: int,
        vector_score: float,
    ) -> None:
        """向候选集添加节点（取最高 vector_score）。"""
        if node.node_id in candidates:
            existing, existing_hop = candidates[node.node_id]
            existing.vector_score = max(existing.vector_score, vector_score)
            # 保留最近跳数
            if hop < existing_hop:
                candidates[node.node_id] = (existing, hop)
        else:
            candidates[node.node_id] = (
                GraphRetrievalResult(
                    node=node,
                    content=node.content,
                    metadata=node.metadata,
                    vector_score=vector_score,
                ),
                hop,
            )

    def _build_context_path(self, node: GraphNode) -> str:
        """构建人类可读的层次路径字符串。"""
        ancestors = list(reversed(self.graph_store.get_ancestors(node.node_id)))

        _LEVEL_FIELD = {
            0: "framework",   # FRAMEWORK
            1: "domain",      # DOMAIN
            2: "category",    # CATEGORY
            3: "control_id",  # CONTROL
            4: "control_id",  # DETAIL
        }

        def _label(n: GraphNode) -> str:
            field = _LEVEL_FIELD.get(n.level, "")
            return n.metadata.get(field) or n.short_id()

        path_parts = [_label(a) for a in ancestors]
        path_parts.append(_label(node))
        return " / ".join(filter(None, path_parts))
