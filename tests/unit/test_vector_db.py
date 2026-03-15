"""单元测试 - Vector DB 模块."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from vector_db.chroma_client import ChromaClient
from vector_db.embedding import EmbeddingModel
from vector_db.persistence import VectorStorePersistence


class TestEmbeddingModel(unittest.TestCase):
    """EmbeddingModel 测试类。"""

    @patch('vector_db.embedding.SentenceTransformer')
    def test_init(self, mock_model):
        """测试初始化。"""
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        model = EmbeddingModel("test-model")
        self.assertEqual(model.model_name, "test-model")

    @patch('vector_db.embedding.SentenceTransformer')
    def test_encode_single(self, mock_model):
        """测试编码单个文本。"""
        import numpy as np
        mock_instance = MagicMock()
        mock_instance.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_model.return_value = mock_instance

        model = EmbeddingModel()
        result = model.encode_single("test")
        self.assertEqual(len(result), 3)


class TestVectorStorePersistence(unittest.TestCase):
    """VectorStorePersistence 测试类。"""

    def setUp(self):
        """测试前准备。"""
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.persistence = VectorStorePersistence(self.temp_dir)

    def test_save_and_load_state(self):
        """测试保存和加载状态。"""
        state = {"chunks": 100, "documents": 50}
        self.persistence.save_state(state)

        loaded = self.persistence.load_state()
        self.assertEqual(loaded["chunks"], 100)
        self.assertIn("last_updated", loaded)

    def test_load_nonexistent_state(self):
        """测试加载不存在的状态。"""
        result = self.persistence.load_state()
        self.assertIsNone(result)

    def test_get_db_size(self):
        """测试获取数据库大小。"""
        size = self.persistence.get_db_size()
        self.assertGreaterEqual(size, 0)


class TestChromaClient(unittest.TestCase):
    """ChromaClient 测试类。"""

    @patch('vector_db.chroma_client.chromadb.PersistentClient')
    def test_init(self, mock_client):
        """测试初始化。"""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        client = ChromaClient("./test_db", "test_collection")
        self.assertEqual(client.collection_name, "test_collection")

    @patch('vector_db.chroma_client.chromadb.PersistentClient')
    def test_add(self, mock_client):
        """测试添加数据。"""
        mock_collection = MagicMock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        client = ChromaClient()
        client.add(
            ids=["1"],
            embeddings=[[0.1, 0.2]],
            documents=["test document"]
        )
        mock_collection.add.assert_called_once()

    @patch('vector_db.chroma_client.chromadb.PersistentClient')
    def test_get_collection_info(self, mock_client):
        """测试获取集合信息。"""
        mock_collection = MagicMock()
        mock_collection.name = "test"
        mock_collection.metadata = {"desc": "test"}
        mock_collection.count.return_value = 10
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        client = ChromaClient()
        info = client.get_collection_info()
        self.assertEqual(info["name"], "test")
        self.assertEqual(info["count"], 10)


if __name__ == "__main__":
    unittest.main()
