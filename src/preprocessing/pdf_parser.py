<<<<<<< HEAD
"""PDF Parser module - Extract text from PDF documents."""

from pathlib import Path
from typing import List, Tuple, Optional

from pypdf import PdfReader


class PDFParser:
    """PDF 文本提取器。

    负责从 PDF 文件中提取文本内容，支持多页提取。

    Attributes:
        pdf_path: PDF 文件路径

    Examples:
        >>> parser = PDFParser("document.pdf")
        >>> pages = parser.extract_text()
        >>> for page_num, text in pages:
        ...     print(f"Page {page_num}: {text[:100]}")
    """

    def __init__(self, pdf_path: str):
        """初始化 PDF 解析器。

        Args:
            pdf_path: PDF 文件路径
        """
        self.pdf_path = Path(pdf_path)
        self._reader: Optional[PdfReader] = None

    @property
    def reader(self) -> PdfReader:
        """懒加载 PDF Reader."""
        if self._reader is None:
            self._reader = PdfReader(str(self.pdf_path))
        return self._reader

    @property
    def num_pages(self) -> int:
        """获取 PDF 页数。"""
        return len(self.reader.pages)

    def extract_text(self) -> List[Tuple[int, str]]:
        """从 PDF 中提取文本。

        Returns:
            包含 (页码，文本) 元组的列表，空页面会被过滤
        """
        pages = []
        for i, page in enumerate(self.reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                pages.append((i, text))
        return pages

    def get_page_text(self, page_num: int) -> str:
        """获取指定页的文本。

        Args:
            page_num: 页码（从 1 开始）

        Returns:
            页面文本，如果页码无效则返回空字符串
        """
        if page_num < 1 or page_num > self.num_pages:
            return ""
        return self.reader.pages[page_num - 1].extract_text()
=======
"""PDF Parser module - Extract text from PDF documents."""

from pathlib import Path
from typing import List, Tuple, Optional

from pypdf import PdfReader


class PDFParser:
    """PDF 文本提取器。

    负责从 PDF 文件中提取文本内容，支持多页提取。

    Attributes:
        pdf_path: PDF 文件路径

    Examples:
        >>> parser = PDFParser("document.pdf")
        >>> pages = parser.extract_text()
        >>> for page_num, text in pages:
        ...     print(f"Page {page_num}: {text[:100]}")
    """

    def __init__(self, pdf_path: str):
        """初始化 PDF 解析器。

        Args:
            pdf_path: PDF 文件路径
        """
        self.pdf_path = Path(pdf_path)
        self._reader: Optional[PdfReader] = None

    @property
    def reader(self) -> PdfReader:
        """懒加载 PDF Reader."""
        if self._reader is None:
            self._reader = PdfReader(str(self.pdf_path))
        return self._reader

    @property
    def num_pages(self) -> int:
        """获取 PDF 页数。"""
        return len(self.reader.pages)

    def extract_text(self) -> List[Tuple[int, str]]:
        """从 PDF 中提取文本。

        Returns:
            包含 (页码，文本) 元组的列表，空页面会被过滤
        """
        pages = []
        for i, page in enumerate(self.reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                pages.append((i, text))
        return pages

    def get_page_text(self, page_num: int) -> str:
        """获取指定页的文本。

        Args:
            page_num: 页码（从 1 开始）

        Returns:
            页面文本，如果页码无效则返回空字符串
        """
        if page_num < 1 or page_num > self.num_pages:
            return ""
        return self.reader.pages[page_num - 1].extract_text()
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
