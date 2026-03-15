"""Report Generator module - Generate execution reports."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ReportEntry:
    """报告条目数据类。

    Attributes:
        rule_id: 规则编号
        status: 状态（success/failed/skipped）
        description: 描述
        timestamp: 时间戳
        details: 详细信息
    """
    rule_id: str
    status: str
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """报告生成器。

    负责生成执行报告和统计信息。

    Attributes:
        report_dir: 报告目录
        report_format: 报告格式（json/markdown/text）

    Examples:
        >>> generator = ReportGenerator("./reports")
        >>> generator.add_entry(entry)
        >>> generator.generate("security_audit")
    """

    def __init__(self, report_dir: str = "./reports", report_format: str = "json"):
        """初始化报告生成器。

        Args:
            report_dir: 报告目录
            report_format: 报告格式
        """
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.report_format = report_format
        self.entries: List[ReportEntry] = []

    def add_entry(self, entry: ReportEntry) -> None:
        """添加报告条目。

        Args:
            entry: 报告条目
        """
        self.entries.append(entry)

    def add_result(
        self,
        rule_id: str,
        status: str,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加执行结果。

        Args:
            rule_id: 规则编号
            status: 状态
            description: 描述
            details: 详细信息
        """
        entry = ReportEntry(
            rule_id=rule_id,
            status=status,
            description=description,
            details=details or {}
        )
        self.entries.append(entry)

    def generate(self, report_name: str) -> str:
        """生成报告。

        Args:
            report_name: 报告名称

        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}"

        if self.report_format == "json":
            return self._generate_json(filename)
        elif self.report_format == "markdown":
            return self._generate_markdown(filename)
        else:
            return self._generate_text(filename)

    def _generate_json(self, filename: str) -> str:
        """生成 JSON 报告。"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_entries": len(self.entries),
            "summary": self._get_summary(),
            "entries": [
                {
                    "rule_id": e.rule_id,
                    "status": e.status,
                    "description": e.description,
                    "timestamp": e.timestamp,
                    "details": e.details
                }
                for e in self.entries
            ]
        }

        filepath = self.report_dir / f"{filename}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def _generate_markdown(self, filename: str) -> str:
        """生成 Markdown 报告。"""
        lines = [
            f"# Security Hardening Report",
            f"",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Rules**: {len(self.entries)}",
            f"",
            f"## Summary",
            f"",
            self._format_summary_markdown(),
            f"",
            f"## Details",
            f""
        ]

        for entry in self.entries:
            status_icon = "✅" if entry.status == "success" else "❌"
            lines.append(
                f"### {status_icon} Rule {entry.rule_id}\n\n"
                f"- **Status**: {entry.status}\n"
                f"- **Description**: {entry.description}\n"
                f"- **Time**: {entry.timestamp}\n"
            )

        filepath = self.report_dir / f"{filename}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return str(filepath)

    def _generate_text(self, filename: str) -> str:
        """生成文本报告。"""
        lines = [
            "=" * 60,
            "SECURITY HARDENING REPORT",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Rules: {len(self.entries)}",
            "",
            self._format_summary_text(),
            "",
            "-" * 60,
            "DETAILS",
            "-" * 60
        ]

        for entry in self.entries:
            lines.append(
                f"\n[{entry.status.upper()}] Rule {entry.rule_id}\n"
                f"  Description: {entry.description}\n"
                f"  Time: {entry.timestamp}"
            )

        filepath = self.report_dir / f"{filename}.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return str(filepath)

    def _get_summary(self) -> Dict[str, Any]:
        """获取统计摘要。"""
        total = len(self.entries)
        success = sum(1 for e in self.entries if e.status == "success")
        failed = sum(1 for e in self.entries if e.status == "failed")
        skipped = sum(1 for e in self.entries if e.status == "skipped")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "success_rate": success / total if total > 0 else 0
        }

    def _format_summary_markdown(self) -> str:
        """格式化 Markdown 摘要。"""
        summary = self._get_summary()
        return (
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| Total | {summary['total']} |\n"
            f"| Success | {summary['success']} |\n"
            f"| Failed | {summary['failed']} |\n"
            f"| Skipped | {summary['skipped']} |\n"
            f"| Success Rate | {summary['success_rate']:.1%} |"
        )

    def _format_summary_text(self) -> str:
        """格式化文本摘要。"""
        summary = self._get_summary()
        return (
            f"Summary:\n"
            f"  Total:     {summary['total']}\n"
            f"  Success:   {summary['success']}\n"
            f"  Failed:    {summary['failed']}\n"
            f"  Skipped:   {summary['skipped']}\n"
            f"  Rate:      {summary['success_rate']:.1%}"
        )

    def clear(self) -> None:
        """清空报告。"""
        self.entries = []
