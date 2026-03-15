"""Ranker module - Rank and re-rank retrieval results."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


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

    def __init__(self):
        """初始化排序器。"""
        pass

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

        for i, result in enumerate(results):
            # 基于原始分数排序
            score = getattr(result, 'score', 1.0 - getattr(result, 'distance', 0))

            ranked_results.append(RankedResult(
                content=getattr(result, 'content', str(result)),
                metadata=getattr(result, 'metadata', {}),
                score=score,
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
