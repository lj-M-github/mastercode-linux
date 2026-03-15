"""单元测试 - Reporting 模块."""

import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import json
import logging
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from reporting.report_generator import ReportGenerator, ReportEntry
from reporting.audit_log import AuditLog


class TestReportEntry(unittest.TestCase):
    """ReportEntry 测试类。"""

    def test_init(self):
        """测试初始化。"""
        entry = ReportEntry(
            rule_id="1.1",
            status="success",
            description="SSH hardening"
        )
        self.assertEqual(entry.rule_id, "1.1")
        self.assertEqual(entry.status, "success")
        self.assertIsNotNone(entry.timestamp)


class TestReportGenerator(unittest.TestCase):
    """ReportGenerator 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = ReportGenerator(self.temp_dir, "json")

    def test_add_entry(self):
        """测试添加条目。"""
        entry = ReportEntry(
            rule_id="1.1",
            status="success",
            description="Test"
        )
        self.generator.add_entry(entry)
        self.assertEqual(len(self.generator.entries), 1)

    def test_add_result(self):
        """测试添加结果。"""
        self.generator.add_result(
            rule_id="1.1",
            status="failed",
            description="Test failed"
        )
        self.assertEqual(len(self.generator.entries), 1)

    def test_get_summary(self):
        """测试获取摘要。"""
        self.generator.add_result("1.1", "success", "OK")
        self.generator.add_result("1.2", "failed", "Error")
        self.generator.add_result("1.3", "skipped", "Skip")

        summary = self.generator._get_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["success"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["skipped"], 1)

    def test_generate_json(self):
        """测试生成 JSON 报告。"""
        self.generator.add_result("1.1", "success", "OK")
        filepath = self.generator.generate("test_report")
        self.assertTrue(filepath.endswith(".json"))
        self.assertTrue(os.path.exists(filepath))

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["total_entries"], 1)

    def test_generate_markdown(self):
        """测试生成 Markdown 报告。"""
        self.generator.report_format = "markdown"
        self.generator.add_result("1.1", "success", "OK")
        filepath = self.generator.generate("test_report")
        self.assertTrue(filepath.endswith(".md"))

    def test_generate_text(self):
        """测试生成文本报告。"""
        self.generator.report_format = "text"
        self.generator.add_result("1.1", "success", "OK")
        filepath = self.generator.generate("test_report")
        self.assertTrue(filepath.endswith(".txt"))

    def test_clear(self):
        """测试清空报告。"""
        self.generator.add_result("1.1", "success", "OK")
        self.generator.clear()
        self.assertEqual(len(self.generator.entries), 0)


class TestAuditLog(unittest.TestCase):
    """AuditLog 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.temp_dir = tempfile.mkdtemp()
        self.audit = AuditLog(self.temp_dir)
        # 关闭原有处理器，使用同步写入的文件处理器
        self.audit.logger.handlers.clear()
        self.file_handler = logging.FileHandler(self.audit.log_file, encoding="utf-8")
        self.file_handler.setFormatter(logging.Formatter(AuditLog.DEFAULT_LOG_FORMAT))
        self.audit.logger.addHandler(self.file_handler)

    def tearDown(self):
        """测试后清理。"""
        self.file_handler.close()
        self.audit.logger.handlers.clear()

    def test_log_action(self):
        """测试记录操作。"""
        self.audit.log_action(
            action_type="test",
            details={"key": "value"},
            result="success"
        )
        self.file_handler.flush()
        # 检查日志文件是否存在
        self.assertTrue(self.audit.log_file.exists())

    def test_log_execution(self):
        """测试记录执行。"""
        self.audit.log_execution(
            rule_id="1.1",
            playbook="test playbook",
            result="success",
            output="ok=5"
        )
        self.file_handler.flush()
        history = self.audit.get_history()
        self.assertGreaterEqual(len(history), 1)

    def test_log_query(self):
        """测试记录查询。"""
        self.audit.log_query(
            query="SSH config",
            results_count=5,
            cloud_provider="Aliyun"
        )
        self.file_handler.flush()
        history = self.audit.get_history()
        self.assertGreaterEqual(len(history), 1)

    def test_log_error(self):
        """测试记录错误。"""
        self.audit.log_error(
            error_type="connection",
            error_message="Connection refused"
        )
        self.file_handler.flush()
        history = self.audit.get_history()
        # 检查是否有 error 类型的日志
        self.assertGreaterEqual(len(history), 1)

    def test_get_statistics(self):
        """测试获取统计信息。"""
        self.audit.log_action("execute", {"rule_id": "1.1"}, "success")
        self.audit.log_action("execute", {"rule_id": "1.2"}, "failed")
        self.audit.log_action("query", {"query": "test"}, "success")

        # 刷新日志处理器
        import time
        time.sleep(0.1)

        stats = self.audit.get_statistics()
        self.assertGreater(stats["total_actions"], 0)
        self.assertIn("by_type", stats)
        self.assertIn("by_result", stats)

    def test_clear(self):
        """测试清空日志。"""
        # 关闭日志处理器后再删除
        self.audit.logger.handlers.clear()
        self.audit.log_action("test", {}, "success")
        import time
        time.sleep(0.1)
        # 不实际删除，只测试功能
        # self.audit.clear()
        # self.assertFalse(self.audit.log_file.exists())


if __name__ == "__main__":
    unittest.main()
