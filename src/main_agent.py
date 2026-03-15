"""Main Agent module - Central orchestration agent for security hardening."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from preprocessing.pdf_parser import PDFParser
from preprocessing.text_cleaner import TextCleaner
from preprocessing.chunker import Chunker
from vector_db.chroma_client import ChromaClient
from vector_db.embedding import EmbeddingModel
from rag.retriever import Retriever
from rag.knowledge_store import KnowledgeStore
from llm.llm_client import LLMClient
from llm.prompt_templates import CODE_GENERATION_SYSTEM_PROMPT, SECURITY_REMEDIATION_TEMPLATE
from executor.ansible_runner import AnsibleRunner
from feedback.result_parser import ResultParser
from feedback.error_analyzer import ErrorAnalyzer
from feedback.self_heal import SelfHealer
from reporting.report_generator import ReportGenerator
from reporting.audit_log import AuditLog


class SecurityHardeningAgent:
    """安全加固主代理。

    统一编排整个安全加固流程：
    1. 知识入库（PDF 解析、分块、向量化）
    2. 知识检索（语义搜索）
    3. 代码生成（LLM 转换）
    4. 执行加固（Ansible）
    5. 自愈循环（错误修复）
    6. 报告生成

    Attributes:
        config: 配置字典
        knowledge_store: 知识库
        llm_client: LLM 客户端
        executor: 执行器
        self_healer: 自愈器
        report_generator: 报告生成器
        audit_log: 审计日志

    Examples:
        >>> agent = SecurityHardeningAgent()
        >>> agent.ingest_knowledge("./doc")
        >>> results = agent.harden("SSH 配置", target_host="localhost")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化安全加固代理。

        Args:
            config: 配置字典
        """
        self.config = config or {}

        # 初始化组件
        self._init_components()

    def _init_components(self) -> None:
        """初始化各组件。"""
        # 知识库
        db_path = self.config.get("db_path", "./vector_db")
        model_name = self.config.get("model_name", "all-MiniLM-L6-v2")
        self.knowledge_store = KnowledgeStore(db_path, "cloud_security_benchmarks", model_name)

        # LLM 客户端
        import os
        self.llm_client = LLMClient(
            model=self.config.get("llm_model", "deepseek-chat"),
            temperature=self.config.get("temperature", 0.1),
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        # 执行器
        self.executor = AnsibleRunner(
            playbook_dir=self.config.get("playbook_dir", "./playbooks")
        )

        # 自愈器
        self.self_healer = SelfHealer(
            llm_client=self.llm_client,
            max_retries=self.config.get("max_retries", 3)
        )

        # 报告生成器
        self.report_generator = ReportGenerator(
            report_dir=self.config.get("report_dir", "./reports")
        )

        # 审计日志
        self.audit_log = AuditLog(
            log_dir=self.config.get("audit_dir", "./audit_logs")
        )

    def ingest_knowledge(self, doc_dir: str) -> Dict[str, Any]:
        """知识入库。

        Args:
            doc_dir: PDF 文档目录

        Returns:
            入库报告
        """
        from preprocessing.pdf_parser import PDFParser
        from preprocessing.text_cleaner import TextCleaner
        from preprocessing.chunker import Chunker
        from rag.knowledge_store import KnowledgeStore

        cleaner = TextCleaner()
        chunker = Chunker()
        knowledge_items = []

        # 处理 PDF 文件
        doc_path = Path(doc_dir)
        for pdf_file in doc_path.glob("*.pdf"):
            parser = PDFParser(str(pdf_file))
            pages = parser.extract_text()

            for page_num, text in pages:
                clean_text = cleaner.clean(text)
                chunks = chunker.split(
                    clean_text,
                    metadata={"source_file": pdf_file.name, "page_number": page_num}
                )

                for chunk in chunks:
                    knowledge_items.append({
                        "content": chunk.content,
                        "metadata": chunk.metadata
                    })

        # 添加到知识库
        count = self.knowledge_store.add(knowledge_items)

        self.audit_log.log_action(
            action_type="ingest",
            details={"doc_dir": doc_dir, "items_added": count}
        )

        return {
            "doc_dir": doc_dir,
            "items_added": count,
            "total_items": self.knowledge_store.get_stats()["total_items"]
        }

    def search_knowledge(
        self,
        query: str,
        n_results: int = 5,
        cloud_provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索知识。

        Args:
            query: 查询文本
            n_results: 结果数量
            cloud_provider: 云厂商

        Returns:
            搜索结果列表
        """
        filter_dict = None
        if cloud_provider:
            filter_dict = {"cloud_provider": cloud_provider}

        results = self.knowledge_store.search(query, n_results, filter_dict)

        self.audit_log.log_query(
            query=query,
            results_count=len(results),
            cloud_provider=cloud_provider or ""
        )

        return [
            {
                "content": r.content,
                "metadata": r.metadata,
                "score": r.score,
                "rank": r.rank
            }
            for r in results
        ]

    def generate_playbook(
        self,
        rule_id: str,
        section_title: str,
        remediation: str,
        cloud_provider: str = "unknown"
    ) -> str:
        """生成 Playbook。

        Args:
            rule_id: 规则编号
            section_title: 章节标题
            remediation: 修复建议
            cloud_provider: 云厂商

        Returns:
            YAML 格式 Playbook
        """
        if not self.llm_client.is_available:
            return self._mock_playbook(rule_id, remediation)

        prompt = SECURITY_REMEDIATION_TEMPLATE.format(
            rule_id=rule_id,
            section_title=section_title,
            remediation=remediation,
            cloud_provider=cloud_provider
        )

        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt=CODE_GENERATION_SYSTEM_PROMPT.build()
        )

        playbook = self._extract_yaml(response.content)
        return playbook or self._mock_playbook(rule_id, remediation)

    def _mock_playbook(self, rule_id: str, remediation: str) -> str:
        """生成模拟 Playbook。"""
        return f"""---
- name: Security hardening for rule {rule_id}
  hosts: localhost
  tasks:
    - name: Apply remediation
      command: echo "{remediation[:100]}"
"""

    def _extract_yaml(self, text: str) -> Optional[str]:
        """提取 YAML 内容。"""
        import re
        yaml_match = re.search(r'```(?:yaml)?\s*(.*?)```', text, re.DOTALL)
        if yaml_match:
            return yaml_match.group(1).strip()

        stripped = text.strip()
        if self._looks_like_yaml(stripped):
            return stripped

        for marker in ("---", "- name:", "- hosts:"):
            index = stripped.find(marker)
            if index != -1:
                candidate = stripped[index:].strip()
                if self._looks_like_yaml(candidate):
                    return candidate

        return None

    def _looks_like_yaml(self, text: str) -> bool:
        """判断文本是否看起来像可执行的 playbook/yaml。"""
        if not text:
            return False

        yaml_indicators = ["hosts:", "tasks:", "- name:", "gather_facts:", "become:"]
        return any(indicator in text for indicator in yaml_indicators)

    def harden(
        self,
        query: str,
        target_host: str = "localhost",
        enable_self_heal: bool = True
    ) -> Dict[str, Any]:
        """执行安全加固。

        Args:
            query: 安全查询（如"SSH 配置"）
            target_host: 目标主机
            enable_self_heal: 是否启用自愈

        Returns:
            执行结果
        """
        # 1. 搜索知识
        search_results = self.search_knowledge(query, n_results=3)

        if not search_results:
            return {"success": False, "error": "No relevant rules found"}

        results = []
        for result in search_results:
            metadata = result["metadata"]

            # 2. 生成 Playbook
            playbook = self.generate_playbook(
                rule_id=metadata.get("rule_id", ""),
                section_title=metadata.get("section_title", ""),
                remediation=metadata.get("remediation", ""),
                cloud_provider=metadata.get("cloud_provider", "")
            )

            # 3. 执行
            exec_result = self.executor.execute(playbook, target_host)

            # 4. 自愈（如果需要）
            if enable_self_heal and not exec_result.success:
                error_context = exec_result.error or exec_result.output
                heal_result = self.self_healer.heal(
                    playbook,
                    error_context,
                    metadata.get("remediation", ""),
                    execute_fn=lambda rewritten: self.executor.execute(rewritten, target_host)
                )
                if heal_result.success:
                    # 自愈回调里已执行过修复后的 playbook，避免重复执行
                    if heal_result.execution_result is not None:
                        exec_result = heal_result.execution_result
                    else:
                        exec_result = self.executor.execute(heal_result.rewritten_playbook, target_host)

            # 5. 记录结果
            self.report_generator.add_result(
                rule_id=metadata.get("rule_id", ""),
                status="success" if exec_result.success else "failed",
                description=metadata.get("section_title", ""),
                details={"output": exec_result.output[:200]}
            )

            self.audit_log.log_execution(
                rule_id=metadata.get("rule_id", ""),
                playbook=playbook,
                result="success" if exec_result.success else "failed"
            )

            results.append({
                "rule_id": metadata.get("rule_id", ""),
                "success": exec_result.success,
                "output": exec_result.output
            })

        return {
            "success": all(r["success"] for r in results),
            "results": results,
            "total": len(results)
        }

    def generate_report(self, report_name: str = "security_hardening") -> str:
        """生成报告。

        Args:
            report_name: 报告名称

        Returns:
            报告文件路径
        """
        return self.report_generator.generate(report_name)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。"""
        return {
            "knowledge_base": self.knowledge_store.get_stats(),
            "llm_available": self.llm_client.is_available,
            "audit_stats": self.audit_log.get_statistics()
        }
