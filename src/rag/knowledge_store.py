"""Knowledge Store module - Unified interface for knowledge management."""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..vector_db.chroma_client import ChromaClient
from ..vector_db.embedding import EmbeddingModel
from ..vector_db.persistence import VectorStorePersistence
from .ranker import Ranker


@dataclass
class RetrievalResult:
    """平铺向量检索结果。"""
    content: str
    metadata: Dict[str, Any]
    score: float
    rank: int
from .graph_builder import GraphBuilder
from .graph_retriever import GraphRetriever, GraphRetrievalResult
from .graph_store import GraphStore

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """知识库。

    统一的知識庫管理接口，封装了向量存储和检索功能。

    Attributes:
        db_path: 数据库路径
        collection_name: 集合名称
        chroma_client: ChromaDB 客户端
        embedding_model: 嵌入模型
        graph_store: 层次知识图谱
        graph_retriever: 图检索器

    Examples:
        >>> store = KnowledgeStore("./vector_db", "my_knowledge")
        >>> store.add(knowledge_items)
        >>> results = store.search("SSH config")
        >>> graph_results = store.graph_search("disable root SSH login", n_results=8)
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        db_path: str = "./vector_db",
        collection_name: str = "knowledge_base",
        model_name: str = DEFAULT_MODEL
    ):
        """初始化知识库。

        Args:
            db_path: 数据库路径
            collection_name: 集合名称
            model_name: 嵌入模型名称
        """
        self.db_path = Path(db_path)
        self.collection_name = collection_name

        # 初始化组件
        self.embedding_model = EmbeddingModel(model_name)
        self.chroma_client = ChromaClient(str(db_path), collection_name)
        self.ranker = Ranker()
        self.persistence = VectorStorePersistence(str(db_path))

        # 层次知识图谱组件
        self.graph_store = GraphStore()
        self._graph_builder = GraphBuilder()
        self.graph_retriever = GraphRetriever(
            self.graph_store, self.chroma_client, self.embedding_model
        )
        self._graph_path = str(self.db_path / "knowledge_graph.json")
        self._try_load_graph()

    def add(
        self,
        items: List[Dict[str, Any]],
        show_progress: bool = False
    ) -> int:
        """添加知识项。

        Args:
            items: 知识项列表，每项包含 content 和 metadata
            show_progress: 是否显示进度

        Returns:
            成功添加的数量
        """
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for item in items:
            content = item.get("content", "")
            metadata = item.get("metadata", {})

            # 生成向量
            embedding = self.embedding_model.encode_single(content)

            ids.append(metadata.get("id", f"item_{len(ids)}"))
            embeddings.append(embedding)
            documents.append(content)
            metadatas.append(metadata)

        self.chroma_client.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        # 同步更新知识图谱
        self._graph_builder.add_items(self.graph_store, items)
        self._save_graph()

        count = len(items)
        # 保存状态
        self.persistence.save_state({
            "last_add_count": count,
            "total": self.get_stats().get("total_items", 0)
        })
        return count

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """搜索知识。

        Args:
            query: 查询文本
            n_results: 返回结果数
            filter_dict: 过滤条件

        Returns:
            检索结果列表
        """
        candidate_n = min(max(n_results * 3, n_results + 5), 50)
        query_embedding = self.embedding_model.encode_single(query)
        raw = self.chroma_client.query(
            query_embeddings=[query_embedding],
            n_results=candidate_n,
            where=filter_dict,
        )
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        candidates = [
            RetrievalResult(content=doc, metadata=meta,
                            score=1.0 - dist, rank=i + 1)
            for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances))
        ]
        ranked = self.ranker.rank(candidates, query=query, top_k=n_results)
        return [
            RetrievalResult(content=r.content, metadata=r.metadata,
                            score=r.score, rank=r.rank)
            for r in ranked
        ]

    def graph_search(
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
        """层次知识图谱混合检索。

        在向量搜索的基础上，利用图结构扩展到相关祖先、兄弟及子节点，
        返回带有层次上下文路径的结果。

        Args:
            query:            查询文本
            n_results:        返回结果数
            seed_k:           向量检索种子数
            expand_siblings:  是否扩展同类别兄弟控制项
            expand_children:  是否扩展实施细节子节点
            expand_ancestors: 是否扩展框架/域/类别上下文
            filter_level:     只返回指定层次（0–4）
            filter_dict:      ChromaDB metadata 过滤条件

        Returns:
            GraphRetrievalResult 列表（含 context_path、final_score）
        """
        if len(self.graph_store) == 0:
            logger.warning("Graph is empty — falling back to vector search")
            flat = self.search(query, n_results=n_results, filter_dict=filter_dict)
            from .graph_node import GraphNode, LEVEL_CONTROL
            return [
                GraphRetrievalResult(
                    node=GraphNode(
                        node_id=r.metadata.get("id", f"vec_{i}"),
                        level=LEVEL_CONTROL,
                        label="CONTROL",
                        content=r.content,
                        metadata=r.metadata,
                    ),
                    content=r.content,
                    metadata=r.metadata,
                    vector_score=r.score,
                    final_score=r.score,
                    rank=r.rank,
                )
                for i, r in enumerate(flat)
            ]
        return self.graph_retriever.search(
            query=query,
            n_results=n_results,
            seed_k=seed_k,
            expand_siblings=expand_siblings,
            expand_children=expand_children,
            expand_ancestors=expand_ancestors,
            filter_level=filter_level,
            filter_dict=filter_dict,
        )

    def get_graph_stats(self) -> Dict[str, Any]:
        """返回知识图谱统计信息。"""
        return self.graph_store.stats()

    def rebuild_graph(self) -> int:
        """从 ChromaDB 全量重建知识图谱。

        Returns:
            构建的 CONTROL 节点数量
        """
        self.graph_store = GraphStore()
        self._graph_builder = GraphBuilder()
        self.graph_retriever = GraphRetriever(
            self.graph_store, self.chroma_client, self.embedding_model
        )
        # 从向量库读取所有文档
        all_items = self._fetch_all_items()
        count = self._graph_builder.add_items(self.graph_store, all_items)
        self._save_graph()
        logger.info("Graph rebuilt: %d CONTROL nodes", count)
        return count

    # ------------------------------------------------------------------
    # Graph persistence helpers
    # ------------------------------------------------------------------

    def _try_load_graph(self) -> None:
        """尝试从磁盘加载已有图谱快照。"""
        import os
        if os.path.exists(self._graph_path):
            try:
                self.graph_store = GraphStore.load(self._graph_path)
                self.graph_retriever = GraphRetriever(
                    self.graph_store, self.chroma_client, self.embedding_model
                )
                logger.info("Knowledge graph loaded from %s (%d nodes)",
                            self._graph_path, len(self.graph_store))
            except Exception as exc:
                logger.warning("Failed to load graph (%s); starting fresh", exc)

    def _save_graph(self) -> None:
        """将图谱状态持久化到磁盘。"""
        try:
            self.graph_store.save(self._graph_path)
        except Exception as exc:
            logger.warning("Failed to save graph: %s", exc)

    def _fetch_all_items(self) -> List[Dict[str, Any]]:
        """从 ChromaDB 拉取全量文档，转换为标准 knowledge item 格式。"""
        try:
            raw = self.chroma_client.collection.get(include=["documents", "metadatas"])
            docs = raw.get("documents") or []
            metas = raw.get("metadatas") or [{}] * len(docs)
            ids = raw.get("ids") or []
            items = []
            for doc, meta, item_id in zip(docs, metas, ids):
                m = dict(meta or {})
                m.setdefault("id", item_id)
                items.append({"content": doc, "metadata": m})
            return items
        except Exception as exc:
            logger.warning("_fetch_all_items failed: %s", exc)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。

        Returns:
            统计信息字典
        """
        info = self.chroma_client.get_collection_info()
        return {
            "collection_name": info["name"],
            "total_items": info["count"],
            "db_path": str(self.db_path)
        }

    def consolidate(
        self,
        rule_id: str,
        playbook: str,
        os_version: str,
        error_signature: str = "",
        version: str = "1",
    ) -> None:
        """Store a verified-successful remediation (knowledge consolidation).

        Per fix.md: ONLY store successful remediations.  Tag with OS version,
        rule_id, error signature, and a version counter so stale entries can
        be superseded without polluting the knowledge base.

        Args:
            rule_id:         CIS/policy rule identifier (e.g. "5.2.1").
            playbook:        Ansible playbook YAML that was verified successful.
            os_version:      Target OS version string (e.g. "RHEL 9.2").
            error_signature: Short description of the original error pattern that
                             this playbook resolved; empty if it was a first-run fix.
            version:         Monotonic version tag for this rule+OS combination.
        """
        self.add([{
            "content": playbook,
            "metadata": {
                "rule_id": rule_id,
                "type": "consolidated_remediation",
                "os_version": os_version,
                "error_signature": error_signature,
                "version": version,
                "source": "verified_success",
                "timestamp": datetime.now().isoformat(),
            },
        }])

    def clear(self) -> None:
        """清空知识库。"""
        self.chroma_client.clear()

    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 获取知识项。

        Args:
            item_id: 知识项 ID

        Returns:
            知识项字典，包含 id、content 和 metadata，如果不存在则返回 None
        """
        result = self.chroma_client.get(ids=[item_id])
        if result and result.get("documents"):
            docs = result["documents"]
            metas = result.get("metadatas", [{}])
            if docs and docs[0]:
                return {
                    "id": item_id,
                    "content": docs[0],
                    "metadata": metas[0] if metas else {}
                }
        return None

    def put(
        self,
        item_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """更新或插入知识项。

        Args:
            item_id: 知识项 ID
            content: 知识内容
            metadata: 元数据
        """
        embedding = self.embedding_model.encode_single(content)
        self.chroma_client.update(
            ids=[item_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata or {}]
        )

    def delete(self, item_id: str) -> None:
        """删除知识项。

        Args:
            item_id: 知识项 ID
        """
        self.chroma_client.delete(ids=[item_id])
        # 保存状态
        self.persistence.save_state({"last_delete": item_id})
