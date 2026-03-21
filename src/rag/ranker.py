"""Ranker module - Rank and re-rank retrieval results."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re


@dataclass
class RankedResult:
    """排序结果数据类。

    Attributes:
        content: 文本内容
        metadata: 元数据
        score: 最终分数
        rank: 排名
    """
    content: str
    metadata: Dict[str, Any]
    score: float
    rank: int


class Ranker:
    """排序器。

    负责对检索结果进行重新排序。

    Examples:
        >>> ranker = Ranker()
        >>> ranked = ranker.rank(results, query="SSH security")
    """

    # 常见技术术语的关键词映射（查询 → 相关技术词）
    KEYWORD_EXPANSION = {
        "firewall": ["iptables", "nftables", "ufw", "firewalld", "firewall-cmd", "netfilter"],
        "permission": ["chmod", "chown", "mode", "owner", "group", "umask", "access control"],
        "permissions": ["chmod", "chown", "mode", "owner", "group", "umask", "access control"],
        "kernel": ["sysctl", "kernel parameter", "proc", "sysctl.conf", "net.ipv4", "fs."],
        "password": ["pam", "pwquality", "minlen", "passwd", "password quality", "unix-passwd"],
        "audit": ["auditd", "auditctl", "audit.log", "ausearch", "audisp"],
        "logging": ["rsyslog", "syslog", "journalctl", "systemd-journald", "log"],
        "user": ["useradd", "usermod", "passwd", "shadow", "user account"],
        "users": ["useradd", "usermod", "passwd", "shadow", "user account"],
        "account": ["useradd", "usermod", "passwd", "shadow", "user account"],
        "network": ["ip", "route", "interface", "netstat", "ss", "tcp", "udp"],
        "cron": ["cron", "crontab", "schedule", "at", "anacron"],
        "selinux": ["selinux", "enforcing", "permissive", "policy", "context"],
    }

    def __init__(self):
        """初始化排序器。"""
        # 缓存复杂关键词的正则，避免重复编译造成开销
        self._pattern_cache: Dict[str, re.Pattern[str]] = {}

    def rank(
        self,
        results: List[Any],
        query: str,
        top_k: Optional[int] = None
    ) -> List[RankedResult]:
        """对结果进行排序。

        Args:
            results: 检索结果列表
            query: 查询文本
            top_k: 返回前 K 个结果

        Returns:
            RankedResult 对象列表
        """
        ranked_results = []

        # 扩展查询关键词
        expanded_keywords = self._expand_query_keywords(query)

        for i, result in enumerate(results):
            # 基于原始分数
            base_score = getattr(result, 'score', 1.0 - getattr(result, 'distance', 0))

            content = getattr(result, 'content', "")
            metadata = getattr(result, 'metadata', {})

            # 计算关键词匹配 boost
            keyword_boost = self._calculate_keyword_match_boost(
                content, metadata, expanded_keywords
            )

            # 合并分数：原始分数 + 关键词匹配 boost
            final_score = min(base_score + keyword_boost, 1.0)

            ranked_results.append(RankedResult(
                content=content,
                metadata=metadata,
                score=final_score,
                rank=i + 1
            ))

        # 按分数降序排序
        ranked_results.sort(key=lambda x: x.score, reverse=True)

        # 重新分配排名
        for i, result in enumerate(ranked_results):
            result.rank = i + 1

        # 限制返回数量
        if top_k:
            ranked_results = ranked_results[:top_k]

        return ranked_results

    def _expand_query_keywords(self, query: str) -> List[str]:
        """扩展查询关键词，添加相关技术术语。

        Args:
            query: 原始查询

        Returns:
            扩展后的关键词列表
        """
        keywords = set(re.findall(r"[a-z0-9_.-]+", query.lower()))

        # 添加原始查询中的词根匹配的技术术语
        for root, related in self.KEYWORD_EXPANSION.items():
            if root in query.lower():
                keywords.update(related)

        return list(keywords)

    def _compile_keyword_pattern(self, keyword: str) -> re.Pattern[str]:
        """为复杂关键词构建边界匹配正则并缓存。"""
        cached = self._pattern_cache.get(keyword)
        if cached is not None:
            return cached

        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])")
        self._pattern_cache[keyword] = pattern
        return pattern

    def _keyword_in_text(self, keyword: str, all_text: str, token_set: set) -> bool:
        """判断关键词是否在文本中命中。"""
        kw = keyword.strip().lower()
        if not kw:
            return False

        # 短词采用 token 精确匹配，避免如 "ip" 命中 "permit"
        if len(kw) <= 2:
            return kw in token_set

        # 单词关键词优先使用快速包含判断
        if " " not in kw and "." not in kw and "-" not in kw:
            return kw in all_text

        # 复杂关键词（短语/带符号）使用边界正则
        return bool(self._compile_keyword_pattern(kw).search(all_text))

    def _calculate_keyword_match_boost(
        self,
        content: str,
        metadata: Dict[str, Any],
        keywords: List[str]
    ) -> float:
        """计算关键词匹配的提升分数。

        Args:
            content: 内容文本
            metadata: 元数据
            keywords: 关键词列表

        Returns:
            提升分数 (0.0 - 0.5)
        """
        # 合并所有文本
        all_text = (
            content.lower() + " " +
            " ".join(str(v).lower() for v in metadata.values() if isinstance(v, str))
        )
        token_set = set(re.findall(r"[a-z0-9_.-]+", all_text))
        unique_keywords = list(dict.fromkeys(k.lower() for k in keywords if k and k.strip()))

        # 计算匹配的关键词数量
        matched_count = sum(
            1 for kw in unique_keywords if self._keyword_in_text(kw, all_text, token_set)
        )

        # 匹配越多 boost 越高，最高 0.5
        if len(unique_keywords) == 0:
            return 0.0

        match_ratio = matched_count / len(unique_keywords)
        return min(match_ratio * 0.5, 0.5)

    def filter_by_metadata(
        self,
        results: List[Any],
        metadata_filter: Dict[str, Any]
    ) -> List[Any]:
        """根据元数据过滤结果。

        Args:
            results: 结果列表
            metadata_filter: 元数据过滤条件

        Returns:
            过滤后的结果列表
        """
        filtered = []

        for result in results:
            metadata = getattr(result, 'metadata', {})
            match = all(
                metadata.get(key) == value
                for key, value in metadata_filter.items()
            )
            if match:
                filtered.append(result)

        return filtered

    def boost_by_relevance(
        self,
        results: List[Any],
        query: str,
        boost_fields: Optional[List[str]] = None
    ) -> List[RankedResult]:
        """根据相关性提升分数。

        Args:
            results: 结果列表
            query: 查询文本
            boost_fields: 需要 boost 的字段

        Returns:
            提升后的排序结果
        """
        if boost_fields is None:
            boost_fields = ["content", "section_title"]

        query_terms = query.lower().split()
        ranked_results = []

        for i, result in enumerate(results):
            base_score = getattr(result, 'score', 1.0)
            metadata = getattr(result, 'metadata', {})
            content = getattr(result, 'content', "")

            # 计算 boost
            boost = 1.0
            for field in boost_fields:
                field_value = str(metadata.get(field, "") if field != "content" else content)
                for term in query_terms:
                    if term in field_value.lower():
                        boost += 0.1

            final_score = min(base_score * boost, 1.0)

            ranked_results.append(RankedResult(
                content=content,
                metadata=metadata,
                score=final_score,
                rank=i + 1
            ))

        ranked_results.sort(key=lambda x: x.score, reverse=True)

        for i, result in enumerate(ranked_results):
            result.rank = i + 1

        return ranked_results
