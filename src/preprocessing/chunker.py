<<<<<<< HEAD
"""Chunker module - Split text into manageable chunks."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class TextChunk:
    """文本块数据类。

    Attributes:
        content: 文本内容
        chunk_id: 块唯一标识
        metadata: 元数据
    """
    content: str
    chunk_id: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Chunker:
    """文本分块器。

    将长文本分割成适合向量化和检索的块。

    Attributes:
        chunk_size: 每块最大字符数
        chunk_overlap: 块间重叠字符数
        separators: 分隔符优先级列表

    Examples:
        >>> chunker = Chunker(chunk_size=500, chunk_overlap=50)
        >>> chunks = chunker.split("Long text content...")
    """

    DEFAULT_CHUNK_SIZE = 800
    DEFAULT_CHUNK_OVERLAP = 100
    MIN_CHUNK_LENGTH = 100

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        """初始化分块器。

        Args:
            chunk_size: 每块最大字符数
            chunk_overlap: 块间重叠字符数
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def split(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """分割文本。

        Args:
            text: 待分割文本
            metadata: 元数据，将附加到每个块

        Returns:
            TextChunk 对象列表
        """
        chunks = self._splitter.split_text(text)

        result = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < self.MIN_CHUNK_LENGTH:
                continue

            result.append(TextChunk(
                content=chunk,
                chunk_id=f"chunk_{i}",
                metadata=metadata or {}
            ))

        return result

    def split_with_context(
        self,
        text: str,
        context: Dict[str, Any],
        id_prefix: str = ""
    ) -> List[TextChunk]:
        """分割文本并附加上下文信息。

        Args:
            text: 待分割文本
            context: 上下文信息（如 rule_id, source_file 等）
            id_prefix: ID 前缀

        Returns:
            TextChunk 对象列表
        """
        chunks = self._splitter.split_text(text)

        result = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < self.MIN_CHUNK_LENGTH:
                continue

            chunk_id = f"{id_prefix}_c{i}" if id_prefix else f"chunk_{i}"

            result.append(TextChunk(
                content=chunk,
                chunk_id=chunk_id,
                metadata=context.copy()
            ))

        return result
=======
"""Chunker module - Split text into manageable chunks."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class TextChunk:
    """文本块数据类。

    Attributes:
        content: 文本内容
        chunk_id: 块唯一标识
        metadata: 元数据
    """
    content: str
    chunk_id: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Chunker:
    """文本分块器。

    将长文本分割成适合向量化和检索的块。

    Attributes:
        chunk_size: 每块最大字符数
        chunk_overlap: 块间重叠字符数
        separators: 分隔符优先级列表

    Examples:
        >>> chunker = Chunker(chunk_size=500, chunk_overlap=50)
        >>> chunks = chunker.split("Long text content...")
    """

    DEFAULT_CHUNK_SIZE = 800
    DEFAULT_CHUNK_OVERLAP = 100
    MIN_CHUNK_LENGTH = 100

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        """初始化分块器。

        Args:
            chunk_size: 每块最大字符数
            chunk_overlap: 块间重叠字符数
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def split(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """分割文本。

        Args:
            text: 待分割文本
            metadata: 元数据，将附加到每个块

        Returns:
            TextChunk 对象列表
        """
        chunks = self._splitter.split_text(text)

        result = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < self.MIN_CHUNK_LENGTH:
                continue

            result.append(TextChunk(
                content=chunk,
                chunk_id=f"chunk_{i}",
                metadata=metadata or {}
            ))

        return result

    def split_with_context(
        self,
        text: str,
        context: Dict[str, Any],
        id_prefix: str = ""
    ) -> List[TextChunk]:
        """分割文本并附加上下文信息。

        Args:
            text: 待分割文本
            context: 上下文信息（如 rule_id, source_file 等）
            id_prefix: ID 前缀

        Returns:
            TextChunk 对象列表
        """
        chunks = self._splitter.split_text(text)

        result = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < self.MIN_CHUNK_LENGTH:
                continue

            chunk_id = f"{id_prefix}_c{i}" if id_prefix else f"chunk_{i}"

            result.append(TextChunk(
                content=chunk,
                chunk_id=chunk_id,
                metadata=context.copy()
            ))

        return result
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
