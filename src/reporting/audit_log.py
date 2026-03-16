import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


class AuditLog:
    """审计日志。

    记录所有操作的审计追踪日志。

    Attributes:
        log_dir: 日志目录
        log_file: 日志文件路径
        logger: 日志记录器

    Examples:
        >>> audit = AuditLog("./audit_logs")
        >>> audit.log_action("execute", {"rule_id": "1.1", "action": "ssh_hardening"})
        >>> audit.get_history("1.1")
    """

    DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

    def __init__(self, log_dir: str = "./audit_logs"):
        """初始化审计日志。

        Args:
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 设置日志文件
        timestamp = datetime.now().strftime("%Y%m%d")
        self.log_file = self.log_dir / f"audit_{timestamp}.log"

        # 配置日志
        self._setup_logger()

    def _setup_logger(self) -> None:
        """配置日志记录器。"""
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(self.DEFAULT_LOG_FORMAT))

        # 避免重复添加
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)

    def log_action(
        self,
        action_type: str,
        details: Dict[str, Any],
        result: str = "success"
    ) -> None:
        """记录操作日志。

        Args:
            action_type: 操作类型（execute/query/modify/delete）
            details: 操作详情
            result: 操作结果
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "details": details,
            "result": result
        }

        self.logger.info(json.dumps(log_entry, ensure_ascii=False))

    def log_execution(
        self,
        rule_id: str,
        playbook: str,
        result: str,
        output: str = ""
    ) -> None:
        """记录执行日志。

        Args:
            rule_id: 规则编号
            playbook: Playbook 内容
            result: 执行结果
            output: 执行输出
        """
        self.log_action(
            action_type="execute",
            details={
                "rule_id": rule_id,
                "playbook": playbook[:500],  # 限制长度
                "output": output[:500]
            },
            result=result
        )

    def log_query(
        self,
        query: str,
        results_count: int,
        cloud_provider: str = ""
    ) -> None:
        """记录查询日志。

        Args:
            query: 查询内容
            results_count: 结果数量
            cloud_provider: 云厂商
        """
        self.log_action(
            action_type="query",
            details={
                "query": query,
                "results_count": results_count,
                "cloud_provider": cloud_provider
            },
            result="success"
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录错误日志。

        Args:
            error_type: 错误类型
            error_message: 错误消息
            context: 上下文信息
        """
        self.log_action(
            action_type="error",
            details={
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {}
            },
            result="failed"
        )

    def get_history(
        self,
        rule_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取历史记录。

        Args:
            rule_id: 规则编号过滤
            action_type: 操作类型过滤
            limit: 限制返回数量

        Returns:
            历史记录列表
        """
        history = []

        if not self.log_file.exists():
            return history

        # 先刷新并关闭日志处理器，确保内容写入文件
        for handler in self.logger.handlers:
            handler.flush()

        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    # 解析日志条目 - 支持多种格式
                    json_part = None
                    if " - INFO - " in line:
                        json_part = line.split(" - INFO - ", 1)[1]
                    elif "INFO" in line:
                        # 尝试直接查找 JSON 部分
                        import re
                        match = re.search(r'\{.*\}', line)
                        if match:
                            json_part = match.group()

                    if json_part:
                        entry = json.loads(json_part)

                        # 过滤
                        if rule_id and rule_id not in str(entry.get("details", {})):
                            continue
                        if action_type and entry.get("action_type") != action_type:
                            continue

                        history.append(entry)

                        if len(history) >= limit:
                            break
                except (json.JSONDecodeError, IndexError, ValueError):
                    continue

        return history

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息。

        Returns:
            统计信息字典
        """
        history = self.get_history(limit=10000)

        stats: Dict[str, Any] = {
            "total_actions": len(history),
            "by_type": {},
            "by_result": {"success": 0, "failed": 0}
        }

        for entry in history:
            action_type = entry.get("action_type", "unknown")
            result = entry.get("result", "unknown")

            stats["by_type"][action_type] = stats["by_type"].get(action_type, 0) + 1
            stats["by_result"][result] = stats["by_result"].get(result, 0) + 1

        return stats

    def clear(self) -> None:
        """清空日志。"""
        if self.log_file.exists():
            self.log_file.unlink()