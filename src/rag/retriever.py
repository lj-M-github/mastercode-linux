<<<<<<< HEAD
"""Retriever module - Retrieve relevant documents from vector store."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from vector_db.chroma_client import ChromaClient
from vector_db.embedding import EmbeddingModel


@dataclass
class RetrievalResult:
    """检索结果数据类。

    Attributes:
        content: 匹配的文本内容
        metadata: 元数据
        score: 相关性分数
        rank: 排名
    """
    content: str
    metadata: Dict[str, Any]
    score: float
    rank: int


class Retriever:
    """检索器。

    负责从向量数据库中检索相关文档。

    Attributes:
        chroma_client: ChromaDB 客户端
        embedding_model: 嵌入模型
        default_n_results: 默认返回结果数

    Examples:
        >>> retriever = Retriever(chroma_client, embedding_model)
        >>> results = retriever.search("SSH configuration", n_results=5)
    """

    def __init__(
        self,
        chroma_client: ChromaClient,
        embedding_model: EmbeddingModel,
        default_n_results: int = 5
    ):
        """初始化检索器。

        Args:
            chroma_client: ChromaDB 客户端
            embedding_model: 嵌入模型
            default_n_results: 默认返回结果数
        """
        self.chroma_client = chroma_client
        self.embedding_model = embedding_model
        self.default_n_results = default_n_results

    def search(
        self,
        query: str,
        n_results: Optional[int] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """搜索相关文档。

        Args:
            query: 查询文本
            n_results: 返回结果数
            filter_dict: 过滤条件

        Returns:
            RetrievalResult 对象列表
        """
        n_results = n_results or self.default_n_results

        # 生成查询向量
        query_embedding = self.embedding_model.encode_single(query)

        # 执行搜索
        results = self.chroma_client.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict
        )

        # 解析结果
        retrieval_results = []
        for i in range(len(results["documents"][0])):
            retrieval_results.append(RetrievalResult(
                content=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
                score=1.0 - results["distances"][0][i],  # 距离转分数
                rank=i + 1
            ))

        return retrieval_results

    def search_by_embedding(
        self,
        embedding: List[float],
        n_results: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """通过向量搜索。

        Args:
            embedding: 查询向量
            n_results: 返回结果数
            filter_dict: 过滤条件

        Returns:
            RetrievalResult 对象列表
        """
        results = self.chroma_client.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=filter_dict
        )

        retrieval_results = []
        for i in range(len(results["documents"][0])):
            retrieval_results.append(RetrievalResult(
                content=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
                score=1.0 - results["distances"][0][i],
                rank=i + 1
            ))

        return retrieval_results
=======
"""Retriever module - Retrieve relevant documents from vector store."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from vector_db.chroma_client import ChromaClient
from vector_db.embedding import EmbeddingModel


@dataclass
class RetrievalResult:
    """检索结果数据类。

    Attributes:
        content: 匹配的文本内容
        metadata: 元数据
        score: 相关性分数
        rank: 排名
    """
    content: str
    metadata: Dict[str, Any]
    score: float
    rank: int


class Retriever:
    """检索器。

    负责从向量数据库中检索相关文档。

    Attributes:
        chroma_client: ChromaDB 客户端
        embedding_model: 嵌入模型
        default_n_results: 默认返回结果数

    Examples:
        >>> retriever = Retriever(chroma_client, embedding_model)
        >>> results = retriever.search("SSH configuration", n_results=5)
    """

    def __init__(
        self,
        chroma_client: ChromaClient,
        embedding_model: EmbeddingModel,
        default_n_results: int = 5
    ):
        """初始化检索器。

        Args:
            chroma_client: ChromaDB 客户端
            embedding_model: 嵌入模型
            default_n_results: 默认返回结果数
        """
        self.chroma_client = chroma_client
        self.embedding_model = embedding_model
        self.default_n_results = default_n_results

    def search(
        self,
        query: str,
        n_results: Optional[int] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """搜索相关文档。

        Args:
            query: 查询文本
            n_results: 返回结果数
            filter_dict: 过滤条件

        Returns:
            RetrievalResult 对象列表
        """
        n_results = n_results or self.default_n_results

        # 生成查询向量
        query_embedding = self.embedding_model.encode_single(query)

        # 执行搜索
        results = self.chroma_client.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict
        )

        # 解析结果
        retrieval_results = []
        for i in range(len(results["documents"][0])):
            retrieval_results.append(RetrievalResult(
                content=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
                score=1.0 - results["distances"][0][i],  # 距离转分数
                rank=i + 1
            ))

        return retrieval_results

    def search_by_embedding(
        self,
        embedding: List[float],
        n_results: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """通过向量搜索。

        Args:
            embedding: 查询向量
            n_results: 返回结果数
            filter_dict: 过滤条件

        Returns:
            RetrievalResult 对象列表
        """
        results = self.chroma_client.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=filter_dict
        )

        retrieval_results = []
        for i in range(len(results["documents"][0])):
            retrieval_results.append(RetrievalResult(
                content=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
                score=1.0 - results["distances"][0][i],
                rank=i + 1
            ))

        return retrieval_results
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
