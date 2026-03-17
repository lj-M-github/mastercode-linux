"""单元测试 - RAG 模块."""

from unittest.mock import MagicMock, patch
import pytest

from src.rag.retriever import Retriever, RetrievalResult
from src.rag.ranker import Ranker, RankedResult
from src.rag.knowledge_store import KnowledgeStore


class TestRetriever:
    """Retriever 测试类。"""

    @pytest.fixture
    def retriever(self):
        """测试前准备。"""
        mock_chroma = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.encode_single.return_value = [0.1, 0.2, 0.3]

        mock_chroma.query.return_value = {
            "documents": [["test document"]],
            "metadatas": [[{"source": "test"}]],
            "distances": [[0.2]]
        }

        return Retriever(
            mock_chroma,
            mock_embedding,
            default_n_results=5
        )

    def test_search(self, retriever):
        """测试搜索。"""
        results = retriever.search("test query", n_results=5)
        assert len(results) == 1
        assert isinstance(results[0], RetrievalResult)

    def test_search_by_embedding(self, retriever):
        """测试通过向量搜索。"""
        results = retriever.search_by_embedding([0.1, 0.2, 0.3])
        assert len(results) >= 0


class TestRanker:
    """Ranker 测试类。"""

    @pytest.fixture
    def ranker(self):
        """测试前准备。"""
        return Ranker()

    def test_rank(self, ranker):
        """测试排序。"""
        mock_results = [
            RetrievalResult(content="doc1", metadata={}, score=0.8, rank=1),
            RetrievalResult(content="doc2", metadata={}, score=0.9, rank=2)
        ]
        ranked = ranker.rank(mock_results, "test")
        assert ranked[0].score == 0.9
        assert ranked[0].rank == 1

    def test_filter_by_metadata(self, ranker):
        """测试元数据过滤。"""
        mock_results = [
            RetrievalResult(content="doc1", metadata={"type": "A"}, score=0.8, rank=1),
            RetrievalResult(content="doc2", metadata={"type": "B"}, score=0.9, rank=2)
        ]
        filtered = ranker.filter_by_metadata(mock_results, {"type": "A"})
        assert len(filtered) == 1

    def test_boost_by_relevance(self, ranker):
        """测试相关性提升。"""
        mock_results = [
            RetrievalResult(content="SSH configuration", metadata={}, score=0.8, rank=1)
        ]
        ranked = ranker.boost_by_relevance(mock_results, "SSH")
        assert len(ranked) >= 1


class TestKnowledgeStore:
    """KnowledgeStore 测试类。"""

    def test_init_with_mock(self):
        """测试初始化（使用 mock）。"""
        from unittest.mock import patch, MagicMock

        # Mock 嵌入模型
        with patch('src.rag.knowledge_store.EmbeddingModel') as MockEmbedding:
            mock_embedding = MagicMock()
            MockEmbedding.return_value = mock_embedding

            # Mock ChromaDB 客户端
            with patch('src.rag.knowledge_store.ChromaClient') as MockChroma:
                mock_chroma = MagicMock()
                MockChroma.return_value = mock_chroma

                store = KnowledgeStore("./test_db", "test_collection")
                assert store is not None
                assert store.collection_name == "test_collection"
