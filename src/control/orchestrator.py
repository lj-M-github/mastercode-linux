"""Orchestrator - Coordinates workflow execution across layers.

Central coordinator that manages the interaction between Deterministic Layer,
AI Layer, and Control Layer components.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path

from ..compliance.drift_auditor import DriftAuditor
from ..compliance.rule_model import DriftResult
from ..llm.llm_client import LLMClient
from ..executor.ansible_runner import AnsibleRunner
from ..rag.knowledge_store import KnowledgeStore
from .state_manager import StateManager, ComplianceState
from .retry_controller import RetryController, FailureType


class Orchestrator:
    """Central orchestrator for compliance remediation workflow.

    Coordinates execution across all layers while maintaining separation
    of deterministic and AI-driven processes.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Initialize components
        self.state_manager = StateManager(
            max_retries=config.get('max_retries', 3)
        )
        self.retry_controller = RetryController(
            max_retry_count=config.get('max_retries', 3)
        )

        # Layer components
        self.drift_auditor = None  # Will be initialized with SSH client
        self.llm_client = LLMClient(
            model=config.get('llm_model', 'deepseek-chat'),
            model_config_path=config.get('model_config_path', './configs/model_selector.yaml')
        )
        self.ansible_runner = AnsibleRunner(
            playbook_dir=config.get('playbook_dir', './playbooks'),
            inventory=config.get('ansible_inventory', '')
        )
        self.knowledge_store = KnowledgeStore(
            db_path=config.get('db_path', './vector_db'),
            collection_name=config.get('collection_name', 'cloud_security_benchmarks'),
            model_name=config.get('model_name', 'all-MiniLM-L6-v2')
        )

    def initialize_drift_auditor(self, checks_file: str, ssh_client=None):
        """Initialize drift auditor with compliance checks."""
        self.drift_auditor = DriftAuditor(
            checks_file=checks_file,
            ssh_client=ssh_client,
            timeout=self.config.get('audit_timeout', 15)
        )

    def audit_compliance(self, rule_ids: List[str]) -> List[DriftResult]:
        """Execute deterministic compliance audit (Deterministic Layer)."""
        if not self.drift_auditor:
            raise RuntimeError("Drift auditor not initialized")

        results = []
        for rule_id in rule_ids:
            result = self.drift_auditor.audit_rule(rule_id)
            results.append(result)

            # Update state based on audit result
            if result.is_compliant:
                self.state_manager.transition(
                    ComplianceState.COMPLIANT,
                    "Audit passed",
                    rule_id=rule_id,
                    metadata={"drift_count": 0}
                )
            else:
                self.state_manager.transition(
                    ComplianceState.DRIFT_DETECTED,
                    f"Detected {len(result.drifts)} drifts",
                    rule_id=rule_id,
                    metadata={"drift_count": len(result.drifts)}
                )

        return results

    def retrieve_knowledge(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge from RAG (AI Layer)."""
        return self.knowledge_store.search(query, n_results=n_results)

    def generate_remediation(self, rule_id: str, drift_result: DriftResult) -> str:
        """Generate remediation playbook using LLM (AI Layer)."""
        # Retrieve relevant knowledge
        query = f"{drift_result.title} {drift_result.domain} remediation"
        knowledge = self.retrieve_knowledge(query, n_results=3)

        # Build context for LLM
        context = f"Rule: {rule_id} - {drift_result.title}\n"
        context += f"Domain: {drift_result.domain}\n"
        context += f"Drifts detected: {len(drift_result.drifts)}\n"

        for drift in drift_result.drifts:
            context += f"- {drift.key}: expected '{drift.expected}', actual '{drift.actual}'\n"

        if knowledge:
            context += "\nRelevant knowledge:\n"
            for item in knowledge:
                context += f"- {item.metadata.get('title', 'Unknown')}: {item.content[:200]}...\n"

        # Generate playbook using LLM
        prompt = f"""Generate an Ansible playbook to remediate the following compliance drift:

{context}

Requirements:
- Use Ansible modules appropriate for the security domain
- Include proper error handling
- Ensure idempotent operations
- Target localhost or remote hosts as needed

Output only the Ansible playbook YAML content."""

        response = self.llm_client.generate(prompt)
        playbook_content = response.content if hasattr(response, 'content') else response

        # Strip markdown code fences from LLM response
        lines = playbook_content.strip().splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        playbook_content = "\n".join(lines).strip()

        # Update state
        self.state_manager.transition(
            ComplianceState.REMEDIATION_GENERATED,
            "Generated remediation playbook",
            rule_id=rule_id,
            metadata={"playbook_length": len(playbook_content)}
        )

        return playbook_content

    def execute_remediation(self, rule_id: str, playbook_content: str,
                          target_host: str = "localhost") -> Dict[str, Any]:
        """Execute remediation playbook (Executor integration)."""
        try:
            # Save playbook to file
            playbook_path = self.ansible_runner.save_playbook(playbook_content, rule_id)

            # Execute playbook — when inventory file is configured, let Ansible use it directly
            limit = target_host if target_host != "localhost" and not self.ansible_runner.inventory else None
            result = self.ansible_runner.run_playbook(
                playbook_name=playbook_path,
                limit=limit
            )

            # Convert ExecutionResult to dict
            result_dict = {
                "success": result.success,
                "error": result.error,
                "output": result.output,
                "steps_executed": result.steps_executed,
                "steps_failed": result.steps_failed,
            }

            if result.success:
                self.state_manager.transition(
                    ComplianceState.REMEDIATION_SUCCEEDED,
                    "Remediation executed successfully",
                    rule_id=rule_id,
                    metadata=result_dict
                )
            else:
                # Record failure
                failure_type = self.retry_controller.categorize_error(result.error)
                self.retry_controller.record_failure(
                    rule_id=rule_id,
                    error_message=result.error,
                    failure_type=failure_type,
                    remediation_command=playbook_content[:100]
                )

                self.state_manager.transition(
                    ComplianceState.EXECUTION_FAILED,
                    f"Execution failed: {result.error}",
                    rule_id=rule_id,
                    metadata=result_dict
                )

            return result_dict

        except Exception as e:
            error_msg = str(e)
            failure_type = self.retry_controller.categorize_error(error_msg)
            self.retry_controller.record_failure(
                rule_id=rule_id,
                error_message=error_msg,
                failure_type=failure_type
            )

            self.state_manager.transition(
                ComplianceState.EXECUTION_FAILED,
                f"Execution exception: {error_msg}",
                rule_id=rule_id,
                metadata={"exception": error_msg}
            )

            return {"success": False, "error": error_msg}

    def verify_remediation(self, rule_id: str) -> DriftResult:
        """Verify remediation effectiveness through re-audit (Deterministic Layer)."""
        if not self.drift_auditor:
            raise RuntimeError("Drift auditor not initialized")

        result = self.drift_auditor.audit_rule(rule_id)

        if result.is_compliant:
            self.state_manager.transition(
                ComplianceState.COMPLIANT,
                "Verification passed - remediation successful",
                rule_id=rule_id,
                metadata={"drift_count": 0}
            )
        else:
            self.state_manager.transition(
                ComplianceState.VERIFICATION_FAILED,
                f"Verification failed - {len(result.drifts)} drifts remain",
                rule_id=rule_id,
                metadata={"drift_count": len(result.drifts)}
            )

        return result

    def process_rule(self, rule_id: str, target_host: str = "localhost") -> Dict[str, Any]:
        """Complete remediation workflow for a single rule."""
        # Initial audit
        audit_results = self.audit_compliance([rule_id])
        drift_result = audit_results[0]

        if drift_result.is_compliant:
            return {
                "success": True,
                "message": "Rule already compliant",
                "final_state": ComplianceState.COMPLIANT.value
            }

        previous_drift_count = None  # First attempt: no convergence check

        # Remediation loop with controlled retries
        while self.retry_controller.should_retry(rule_id, len(drift_result.drifts), previous_drift_count):
            # Generate remediation
            playbook = self.generate_remediation(rule_id, drift_result)

            # Execute remediation
            exec_result = self.execute_remediation(rule_id, playbook, target_host)

            if exec_result['success']:
                # Verify remediation
                verification_result = self.verify_remediation(rule_id)

                if verification_result.is_compliant:
                    return {
                        "success": True,
                        "message": "Remediation successful",
                        "final_state": ComplianceState.COMPLIANT.value,
                        "attempts": self.retry_controller.rule_attempts.get(rule_id, 1)
                    }
                else:
                    # Verification failed - prepare for retry
                    drift_result = verification_result
                    previous_drift_count = len(drift_result.drifts)
            else:
                # Execution failed - will retry if allowed
                previous_drift_count = len(drift_result.drifts)

        # Max retries exceeded
        self.state_manager.transition(
            ComplianceState.UNRESOLVED,
            "Maximum retry attempts exceeded",
            rule_id=rule_id
        )

        return {
            "success": False,
            "message": "Remediation failed after maximum retries",
            "final_state": ComplianceState.UNRESOLVED.value,
            "attempts": self.retry_controller.rule_attempts.get(rule_id, 0)
        }

    def get_workflow_status(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current workflow status and statistics."""
        current_state = self.state_manager.get_current_state(rule_id)
        history = self.state_manager.get_transition_history(rule_id)
        retry_stats = self.retry_controller.get_retry_statistics()

        return {
            "current_state": current_state.value,
            "transition_count": len(history),
            "retry_statistics": retry_stats,
            "is_terminal": self.state_manager.is_terminal_state(current_state)
        }