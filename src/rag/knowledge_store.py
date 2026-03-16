<<<<<<< HEAD
"""Knowledge Store module - Unified interface for knowledge management."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from vector_db.chroma_client import ChromaClient
from vector_db.embedding import EmbeddingModel
from rag.retriever import Retriever, RetrievalResult


class KnowledgeStore:
    """知识库。

    统一的知識庫管理接口，封装了向量存储和检索功能。

    Attributes:
        db_path: 数据库路径
        collection_name: 集合名称
        chroma_client: ChromaDB 客户端
        embedding_model: 嵌入模型
        retriever: 检索器

    Examples:
        >>> store = KnowledgeStore("./vector_db", "my_knowledge")
        >>> store.add(knowledge_items)
        >>> results = store.search("SSH config")
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
        self.retriever = Retriever(self.chroma_client, self.embedding_model)

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

        return len(items)

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
        return self.retriever.search(query, n_results, filter_dict)

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

    def clear(self) -> None:
        """清空知识库。"""
        self.chroma_client.clear()
=======
"""Knowledge Store module - Unified interface for knowledge management."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from vector_db.chroma_client import ChromaClient
from vector_db.embedding import EmbeddingModel
from rag.retriever import Retriever, RetrievalResult


class KnowledgeStore:
    """知识库。

    统一的知識庫管理接口，封装了向量存储和检索功能。

    Attributes:
        db_path: 数据库路径
        collection_name: 集合名称
        chroma_client: ChromaDB 客户端
        embedding_model: 嵌入模型
        retriever: 检索器

    Examples:
        >>> store = KnowledgeStore("./vector_db", "my_knowledge")
        >>> store.add(knowledge_items)
        >>> results = store.search("SSH config")
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
        self.retriever = Retriever(self.chroma_client, self.embedding_model)

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

        return len(items)

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
        return self.retriever.search(query, n_results, filter_dict)

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

    def clear(self) -> None:
        """清空知识库。"""
        self.chroma_client.clear()
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
