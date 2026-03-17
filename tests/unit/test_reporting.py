"""单元测试 - Reporting 模块."""

from unittest.mock import patch, MagicMock
import os
import tempfile
import json
import logging
import pytest

from src.reporting.report_generator import ReportGenerator, ReportEntry
from src.reporting.audit_log import AuditLog


class TestReportEntry:
    """ReportEntry 测试类。"""

    def test_init(self):
        """测试初始化。"""
        entry = ReportEntry(
            rule_id="1.1",
            status="success",
            description="SSH hardening"
        )
        assert entry.rule_id == "1.1"
        assert entry.status == "success"
        assert entry.timestamp is not None


class TestReportGenerator:
    """ReportGenerator 测试类。"""

    @pytest.fixture
    def generator(self):
        """测试前准备。"""
        temp_dir = tempfile.mkdtemp()
        return ReportGenerator(temp_dir, "json")

    def test_add_entry(self, generator):
        """测试添加条目。"""
        entry = ReportEntry(
            rule_id="1.1",
            status="success",
            description="Test"
        )
        generator.add_entry(entry)
        assert len(generator.entries) == 1

    def test_add_result(self, generator):
        """测试添加结果。"""
        generator.add_result(
            rule_id="1.1",
            status="failed",
            description="Test failed"
        )
        assert len(generator.entries) == 1

    def test_get_summary(self, generator):
        """测试获取摘要。"""
        generator.add_result("1.1", "success", "OK")
        generator.add_result("1.2", "failed", "Error")
        generator.add_result("1.3", "skipped", "Skip")

        summary = generator._get_summary()
        assert summary["total"] == 3
        assert summary["success"] == 1
        assert summary["failed"] == 1
        assert summary["skipped"] == 1

    def test_generate_json(self, generator):
        """测试生成 JSON 报告。"""
        generator.add_result("1.1", "success", "OK")
        filepath = generator.generate("test_report")
        assert filepath.endswith(".json")
        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_entries"] == 1

    def test_generate_markdown(self, generator):
        """测试生成 Markdown 报告。"""
        generator.report_format = "markdown"
        generator.add_result("1.1", "success", "OK")
        filepath = generator.generate("test_report")
        assert filepath.endswith(".md")

    def test_generate_text(self, generator):
        """测试生成文本报告。"""
        generator.report_format = "text"
        generator.add_result("1.1", "success", "OK")
        filepath = generator.generate("test_report")
        assert filepath.endswith(".txt")

    def test_clear(self, generator):
        """测试清空报告。"""
        generator.add_result("1.1", "success", "OK")
        generator.clear()
        assert len(generator.entries) == 0


class TestAuditLog:
    """AuditLog 测试类。"""

    @pytest.fixture
    def audit(self):
        """测试前准备。"""
        temp_dir = tempfile.mkdtemp()
        audit_log = AuditLog(temp_dir)
        # 关闭原有处理器，使用同步写入的文件处理器
        audit_log.logger.handlers.clear()
        file_handler = logging.FileHandler(audit_log.log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(AuditLog.DEFAULT_LOG_FORMAT))
        audit_log.logger.addHandler(file_handler)
        yield audit_log
        # 清理
        file_handler.close()
        audit_log.logger.handlers.clear()

    def test_log_action(self, audit):
        """测试记录操作。"""
        audit.log_action(
            action_type="test",
            details={"key": "value"},
            result="success"
        )
        audit.logger.handlers[0].flush()
        # 检查日志文件是否存在
        assert audit.log_file.exists()

    def test_log_execution(self, audit):
        """测试记录执行。"""
        audit.log_execution(
            rule_id="1.1",
            playbook="test playbook",
            result="success",
            output="ok=5"
        )
        audit.logger.handlers[0].flush()
        history = audit.get_history()
        assert len(history) >= 1

    def test_log_query(self, audit):
        """测试记录查询。"""
        audit.log_query(
            query="SSH config",
            results_count=5,
            cloud_provider="Aliyun"
        )
        audit.logger.handlers[0].flush()
        history = audit.get_history()
        assert len(history) >= 1

    def test_log_error(self, audit):
        """测试记录错误。"""
        audit.log_error(
            error_type="connection",
            error_message="Connection refused"
        )
        audit.logger.handlers[0].flush()
        history = audit.get_history()
        # 检查是否有 error 类型的日志
        assert len(history) >= 1

    def test_get_statistics(self, audit):
        """测试获取统计信息。"""
        audit.log_action("execute", {"rule_id": "1.1"}, "success")
        audit.log_action("execute", {"rule_id": "1.2"}, "failed")
        audit.log_action("query", {"query": "test"}, "success")

        # 刷新日志处理器
        import time
        time.sleep(0.1)

        stats = audit.get_statistics()
        assert stats["total_actions"] > 0
        assert "by_type" in stats
        assert "by_result" in stats
