"""Main Agent module - Research-grade compliance remediation framework."""

import re
import logging
import json
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
from pathlib import Path

from .control.orchestrator import Orchestrator
from .executor.ssh_client import SSHClient, SSHConfig
from .executor.ansible_runner import AnsibleRunner
from .reporting.report_generator import ReportGenerator
from .reporting.audit_log import AuditLog
from .preprocessing.pdf_parser import PDFParser
from .preprocessing.text_cleaner import TextCleaner
from .preprocessing.chunker import Chunker
from .compliance.drift_auditor import DriftAuditor
from .compliance.rule_model import DriftResult, DriftField
from .compliance.auditor import ComplianceAuditor, ComplianceCheckResult
from .feedback.self_heal import SelfHealer
from .rag.knowledge_store import KnowledgeStore
from .llm.llm_client import LLMClient
from .llm.prompt_templates import (
    CODE_GENERATION_SYSTEM_PROMPT,
    SECURITY_REMEDIATION_TEMPLATE,
)
from .utils.yaml_utils import extract_yaml


class SecurityHardeningAgent:
    """Research-grade autonomous compliance remediation framework.

    Implements drift-aware compliance modeling with deterministic closed-loop verification,
    controlled AI-assisted remediation, and retrieval-constrained generation.

    Architecture:
    - Deterministic Layer: Rule loading, compliance auditing, drift detection, verification
    - AI Layer: RAG retrieval, remediation generation, failure rewriting
    - Control Layer: Orchestration, retry control, state management

    Attributes:
        config: Configuration dictionary
        orchestrator: Central workflow coordinator

    Examples:
        >>> agent = SecurityHardeningAgent()
        >>> agent.ingest_knowledge("./data/policies/cis")
        >>> results = agent.harden("SSH configuration", target_host="localhost")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the compliance remediation framework.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.orchestrator = Orchestrator(self.config)

        # Initialize reporting components
        self.report_generator = ReportGenerator(
            report_dir=self.config.get("report_dir", "./reports")
        )
        self.audit_log = AuditLog(
            log_dir=self.config.get("audit_dir", "./audit_logs")
        )

    def ingest_knowledge(self, doc_dir: str) -> Dict[str, Any]:
        """Knowledge ingestion pipeline (Preprocessing → Vector DB).

        Args:
            doc_dir: Directory containing policy documents (PDF/YAML)

        Returns:
            Ingestion report with statistics
        """
        from .preprocessing.pdf_parser import PDFParser
        from .preprocessing.text_cleaner import TextCleaner
        from .preprocessing.chunker import Chunker

        doc_path = Path(doc_dir)
        knowledge_items = []

        # Process PDF documents
        text_cleaner = TextCleaner()
        chunker = Chunker(chunk_size=1000, chunk_overlap=200)

        for pdf_file in doc_path.glob("**/*.pdf"):
            try:
                pdf_parser = PDFParser(str(pdf_file))
                pages = pdf_parser.extract_text()  # List[Tuple[int, str]]
                for page_num, text in pages:
                    cleaned = text_cleaner.clean(text)
                    chunks = chunker.split(cleaned)
                    for i, chunk in enumerate(chunks):
                        knowledge_items.append({
                            "content": chunk.content,
                            "metadata": {
                                "source_file": str(pdf_file),
                                "page_number": page_num,
                                "chunk_id": i,
                                "doc_type": "pdf"
                            }
                        })
            except Exception as e:
                logger.warning(f"Failed to process {pdf_file}: {e}")

        # Process YAML control files
        self._ingest_yaml_controls(doc_path, knowledge_items)

        # Store in vector database
        count = self.orchestrator.knowledge_store.add(knowledge_items)

        return {
            "items_added": count,
            "total_items": self.orchestrator.knowledge_store.get_stats()["total_items"],
            "sources": list(set(item["metadata"]["source_file"] for item in knowledge_items))
        }

    def _ingest_yaml_controls(self, doc_path: Path, knowledge_items: List[Dict[str, Any]]) -> None:
        """Ingest YAML control files with structured rule metadata."""
        import yaml

        for yml_file in doc_path.glob("*-controls.yml"):
            try:
                raw = yml_file.read_text(encoding="utf-8")
                data = yaml.safe_load(raw)
            except Exception:
                continue

            if not isinstance(data, dict):
                continue

            policy = data.get("policy", "")
            product = data.get("product", "")
            cloud_provider = self._infer_cloud_provider(yml_file.name)

            for ctrl in data.get("controls", []):
                rule_id = str(ctrl.get("id", ""))
                title = ctrl.get("title", "")
                notes = ctrl.get("notes", "")
                rules_list = ctrl.get("rules", [])
                remediation_parts = []
                if notes:
                    remediation_parts.append(notes)
                if rules_list:
                    remediation_parts.append("Related rules: " + ", ".join(str(r) for r in rules_list))
                remediation = "\n".join(remediation_parts)

                content = f"{rule_id} {title}\n{remediation}"
                knowledge_items.append({
                    "content": content,
                    "metadata": {
                        "id": f"{yml_file.stem}_{rule_id}",
                        "rule_id": rule_id,
                        "section_title": title,
                        "remediation": remediation,
                        "cloud_provider": cloud_provider,
                        "source_file": str(yml_file),
                        "policy": policy,
                        "product": product,
                    },
                })

    @staticmethod
    def _infer_cloud_provider(filename: str) -> str:
        """Infer cloud provider from filename."""
        name_lower = filename.lower()
        patterns = {
            "alibaba": "Alibaba", "aliyun": "Alibaba", "alicloud": "Alibaba",
            "tencent": "Tencent",
            "google": "GCP", "gcp": "GCP",
            "aws": "AWS", "amazon": "AWS",
            "azure": "Azure",
            "huawei": "Huawei",
        }
        for keyword, provider in patterns.items():
            if keyword in name_lower:
                return provider
        return "unknown"

    def harden(self, query: str, target_host: str = "localhost",
               enable_self_heal: bool = True,
               rule_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute autonomous compliance remediation workflow.

        Args:
            query: Natural language description of compliance requirements
            target_host: Target host for remediation (localhost or SSH target)
            enable_self_heal: Enable controlled self-healing with retries
            rule_ids: Optional explicit list of rule IDs (bypasses RAG)

        Returns:
            Remediation results with success metrics
        """
        # Initialize drift auditor with SSH if needed
        ssh_client = None
        if target_host != "localhost":
            if "@" in target_host:
                user, host = target_host.split("@", 1)
                ssh_config = SSHConfig(
                    host=host,
                    username=user,
                    key_file=self.config.get("ssh_key_file", "~/.ssh/id_rsa")
                )
                ssh_client = SSHClient(ssh_config)
            else:
                ssh_config = SSHConfig(host=target_host)
                ssh_client = SSHClient(ssh_config)

        checks_file = self.config.get("compliance_checks_file", "./data/compliance_checks/cis_rhel9_checks.yaml")
        self.orchestrator.initialize_drift_auditor(checks_file, ssh_client)

        # Use explicit rule IDs if provided, otherwise retrieve via RAG
        if rule_ids:
            pass  # Use provided rule_ids directly
        else:
            # Retrieve relevant rules using RAG
            relevant_rules = self.orchestrator.retrieve_knowledge(query, n_results=10)
            rule_ids = []
            for item in relevant_rules:
                metadata = item.metadata if hasattr(item, 'metadata') else {}
                rid = metadata.get("rule_id") if isinstance(metadata, dict) else getattr(metadata, 'rule_id', None)
                if rid and rid not in rule_ids:
                    rule_ids.append(rid)

        if not rule_ids:
            return {"success": False, "error": "No relevant compliance rules found"}

        # Process each rule through the remediation workflow
        results = []
        for rule_id in rule_ids:
            result = self.orchestrator.process_rule(rule_id, target_host)
            results.append({
                "rule_id": rule_id,
                "success": result["success"],
                "message": result["message"],
                "final_state": result["final_state"],
                "attempts": result.get("attempts", 0)
            })

        # Calculate success metrics
        successful = sum(1 for r in results if r["success"])
        total = len(results)

        summary = {
            "success": successful > 0,
            "results": results,
            "total": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "workflow_status": self.orchestrator.get_workflow_status()
        }

        # Log results
        self.audit_log.log_action("harden", {
            "query": query,
            "target_host": target_host,
            "results": summary
        })

        return summary

    def audit_compliance(self, rule_ids: List[str], ssh_host: Optional[str] = None,
                        ssh_username: Optional[str] = None, ssh_key_file: Optional[str] = None) -> Dict[str, Any]:
        """Execute deterministic compliance audit.

        Args:
            rule_ids: List of rule IDs to audit
            ssh_host: SSH target host
            ssh_username: SSH username
            ssh_key_file: SSH key file

        Returns:
            Audit results with compliance status
        """
        # Initialize SSH client if needed
        ssh_client = None
        if ssh_host:
            ssh_config = SSHConfig(
                host=ssh_host,
                username=ssh_username or "ec2-user",
                key_file=ssh_key_file or "~/.ssh/id_rsa"
            )
            ssh_client = SSHClient(ssh_config)

        checks_file = self.config.get("compliance_checks_file", "./data/compliance_checks/cis_rhel9_checks.yaml")
        self.orchestrator.initialize_drift_auditor(checks_file, ssh_client)

        # Execute audit
        results = self.orchestrator.audit_compliance(rule_ids)

        # Calculate summary statistics
        total = len(results)
        compliant = sum(1 for r in results if r.is_compliant)
        fail_count = total - compliant

        summary = {
            "total": total,
            "pass_count": compliant,
            "fail_count": fail_count,
            "pass_rate": compliant / total if total > 0 else 0,
            "pass_rate_pct": f"{compliant / total * 100:.1f}%" if total > 0 else "0%",
            "results": [r.to_dict() for r in results]
        }

        # Log audit
        self.audit_log.log_action("audit", summary)

        return summary

    def generate_report(self, title: str) -> str:
        """Generate compliance report.

        Args:
            title: Report title

        Returns:
            Path to generated report
        """
        return self.report_generator.generate(title)

    def get_stats(self) -> Dict[str, Any]:
        """Get framework statistics for evaluation."""
        kb_stats = {
            "collection_name": self.orchestrator.knowledge_store.collection_name,
            "total_items": self.orchestrator.knowledge_store.count()
        }

        workflow_stats = self.orchestrator.get_workflow_status()
        retry_stats = self.orchestrator.retry_controller.get_retry_statistics()

        return {
            "knowledge_base": kb_stats,
            "workflow": workflow_stats,
            "retry_statistics": retry_stats,
            "llm_available": self.orchestrator.llm_client.is_available
        }
