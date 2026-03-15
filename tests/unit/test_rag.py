"""单元测试 - RAG 模块."""

import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from rag.retriever import Retriever, RetrievalResult
from rag.ranker import Ranker, RankedResult
from rag.knowledge_store import KnowledgeStore


class TestRetriever(unittest.TestCase):
    """Retriever 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.mock_chroma = MagicMock()
        self.mock_embedding = MagicMock()
        self.mock_embedding.encode_single.return_value = [0.1, 0.2, 0.3]

        self.mock_chroma.query.return_value = {
            "documents": [["test document"]],
            "metadatas": [[{"source": "test"}]],
            "distances": [[0.2]]
        }

        self.retriever = Retriever(
            self.mock_chroma,
            self.mock_embedding,
            default_n_results=5
        )

    def test_search(self):
        """测试搜索。"""
        results = self.retriever.search("test query", n_results=5)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], RetrievalResult)

    def test_search_by_embedding(self):
        """测试通过向量搜索。"""
        results = self.retriever.search_by_embedding([0.1, 0.2, 0.3])
        self.assertGreaterEqual(len(results), 0)


class TestRanker(unittest.TestCase):
    """Ranker 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.ranker = Ranker()

    def test_rank(self):
        """测试排序。"""
        mock_results = [
            RetrievalResult(content="doc1", metadata={}, score=0.8, rank=1),
            RetrievalResult(content="doc2", metadata={}, score=0.9, rank=2)
        ]
        ranked = self.ranker.rank(mock_results, "test")
        self.assertEqual(ranked[0].score, 0.9)
        self.assertEqual(ranked[0].rank, 1)

    def test_filter_by_metadata(self):
        """测试元数据过滤。"""
        mock_results = [
            RetrievalResult(content="doc1", metadata={"type": "A"}, score=0.8, rank=1),
            RetrievalResult(content="doc2", metadata={"type": "B"}, score=0.9, rank=2)
        ]
        filtered = self.ranker.filter_by_metadata(mock_results, {"type": "A"})
        self.assertEqual(len(filtered), 1)

    def test_boost_by_relevance(self):
        """测试相关性提升。"""
        mock_results = [
            RetrievalResult(content="SSH configuration", metadata={}, score=0.8, rank=1)
        ]
        ranked = self.ranker.boost_by_relevance(mock_results, "SSH")
        self.assertGreaterEqual(len(ranked), 1)


class TestKnowledgeStore(unittest.TestCase):
    """KnowledgeStore 测试类。"""

    def test_init_with_mock(self):
        """测试初始化（使用 mock）。"""
        from unittest.mock import MagicMock, patch

        # Mock 嵌入模型
        with patch('rag.knowledge_store.EmbeddingModel') as MockEmbedding:
            mock_embedding = MagicMock()
            MockEmbedding.return_value = mock_embedding

            # Mock ChromaDB 客户端
            with patch('rag.knowledge_store.ChromaClient') as MockChroma:
                mock_chroma = MagicMock()
                MockChroma.return_value = mock_chroma

                store = KnowledgeStore("./test_db", "test_collection")
                self.assertIsNotNone(store)
                self.assertEqual(store.collection_name, "test_collection")


if __name__ == "__main__":
    unittest.main()
