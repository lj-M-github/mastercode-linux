<<<<<<< HEAD
"""Text Cleaner module - Clean and normalize extracted text."""

import re
from typing import Optional


class TextCleaner:
    """文本清洗器。

    负责清洗从 PDF 提取的文本，移除噪声和标准化格式。

    Examples:
        >>> cleaner = TextCleaner()
        >>> text = cleaner.clean("  Hello\\n\\nWorld  ")
        >>> print(text)
        'Hello World'
    """

    def __init__(self):
        """初始化文本清洗器。"""
        # 常见 PDF 噪声模式
        self.noise_patterns = [
            (r'\n\s*\n', '\n'),  # 多个空行
            (r' +', ' '),  # 多个空格
            (r'[\u200b\u200c\u200d\uFEFF]', ''),  # 零宽字符
            (r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ''),  # 控制字符
        ]

    def clean(self, text: str) -> str:
        """清洗文本。

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        # 移除噪声
        for pattern, replacement in self.noise_patterns:
            text = re.sub(pattern, replacement, text)

        # 移除页眉页脚（常见模式）
        text = self._remove_headers_footers(text)

        # 标准化空白
        text = text.strip()

        return text

    def _remove_headers_footers(self, text: str) -> str:
        """移除页眉页脚。

        Args:
            text: 文本

        Returns:
            移除页眉页脚后的文本
        """
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # 跳过可能是页眉页脚的内容
            if self._is_header_footer(line):
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _is_header_footer(self, line: str) -> bool:
        """判断是否为页眉页脚。

        Args:
            line: 单行文本

        Returns:
            是否为页眉页脚
        """
        # 页码模式
        if re.match(r'^\d+$', line):
            return True
        # 版权信息
        if 'copyright' in line.lower() or '©' in line:
            return True
        # 过短的行（可能是页脚）
        if len(line) < 5:
            return True
        return False

    def normalize_whitespace(self, text: str) -> str:
        """标准化空白字符。

        Args:
            text: 文本

        Returns:
            标准化后的文本
        """
        # 将多个空白替换为单个空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
=======
"""Text Cleaner module - Clean and normalize extracted text."""

import re
from typing import Optional


class TextCleaner:
    """文本清洗器。

    负责清洗从 PDF 提取的文本，移除噪声和标准化格式。

    Examples:
        >>> cleaner = TextCleaner()
        >>> text = cleaner.clean("  Hello\\n\\nWorld  ")
        >>> print(text)
        'Hello World'
    """

    def __init__(self):
        """初始化文本清洗器。"""
        # 常见 PDF 噪声模式
        self.noise_patterns = [
            (r'\n\s*\n', '\n'),  # 多个空行
            (r' +', ' '),  # 多个空格
            (r'[\u200b\u200c\u200d\uFEFF]', ''),  # 零宽字符
            (r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ''),  # 控制字符
        ]

    def clean(self, text: str) -> str:
        """清洗文本。

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        # 移除噪声
        for pattern, replacement in self.noise_patterns:
            text = re.sub(pattern, replacement, text)

        # 移除页眉页脚（常见模式）
        text = self._remove_headers_footers(text)

        # 标准化空白
        text = text.strip()

        return text

    def _remove_headers_footers(self, text: str) -> str:
        """移除页眉页脚。

        Args:
            text: 文本

        Returns:
            移除页眉页脚后的文本
        """
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # 跳过可能是页眉页脚的内容
            if self._is_header_footer(line):
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _is_header_footer(self, line: str) -> bool:
        """判断是否为页眉页脚。

        Args:
            line: 单行文本

        Returns:
            是否为页眉页脚
        """
        # 页码模式
        if re.match(r'^\d+$', line):
            return True
        # 版权信息
        if 'copyright' in line.lower() or '©' in line:
            return True
        # 过短的行（可能是页脚）
        if len(line) < 5:
            return True
        return False

    def normalize_whitespace(self, text: str) -> str:
        """标准化空白字符。

        Args:
            text: 文本

        Returns:
            标准化后的文本
        """
        # 将多个空白替换为单个空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
