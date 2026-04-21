# LLM-Driven Autonomous Compliance Remediation Framework Based on RAG and Closed-Loop Verification

## 1. Research Overview

This master's thesis presents an LLM-driven autonomous compliance remediation framework that integrates Retrieval-Augmented Generation (RAG) with deterministic closed-loop verification. The system transforms static security benchmarks into executable remediation actions while maintaining rigorous compliance verification through structured drift modeling and controlled AI-assisted processes.

The framework addresses the critical gap between policy documentation and automated enforcement by establishing a layered architecture that separates deterministic verification from AI-driven remediation, ensuring both reliability and adaptability in compliance automation.

## 2. Drift Model Design

### Structured Compliance Drift Abstraction

The framework introduces a structured compliance drift model to replace simplistic boolean pass/fail assessments with granular drift representations:

```json
{
  "rule_id": "string",
  "is_compliant": "boolean",
  "drifts": [
    {
      "key": "string",
      "expected": "string|number|boolean",
      "actual": "string|number|boolean",
      "comparison_type": "exact|regex|numeric|boolean"
    }
  ]
}
```

### Theoretical Necessity and Benefits

**Why Drift Modeling is Necessary**: Traditional binary compliance assessments fail to capture the nuanced deviations between expected and actual system states. Drift modeling provides explicit representation of compliance gaps, enabling precise remediation targeting rather than blanket policy application.

**Improvement in Remediation Precision**: By quantifying specific drift parameters (e.g., SSH configuration values, file permissions), the system generates targeted remediation actions that address exact non-compliance causes, reducing unnecessary system modifications and potential service disruptions.

**Strengthening Closed-Loop Verification**: Structured drift representation enables deterministic verification of remediation effectiveness. Each drift component can be individually validated post-remediation, ensuring complete compliance restoration rather than partial fixes.

## 3. Layered Architecture Separation

The framework employs a three-layer architecture that maintains clear separation of concerns between deterministic operations and AI-driven processes:

### Deterministic Layer

**Responsibilities**:
- **Rule Loader**: Parses and validates compliance rule specifications from structured sources (YAML configurations)
- **Compliance Auditor**: Executes deterministic checks against target systems using predefined shell commands and regex patterns
- **Drift Detector**: Compares actual system states against expected values to generate structured drift representations
- **Verification Engine**: Performs post-remediation validation using identical deterministic methods as initial auditing

**Design Rationale**: Audit and verification operations must remain strictly deterministic to ensure reproducibility and reliability. Non-deterministic AI involvement in verification would compromise the scientific validity of compliance assessments and introduce uncertainty in experimental evaluations.

### AI Layer

**Responsibilities**:
- **RAG Retrieval**: Performs semantic search across vectorized security knowledge bases to retrieve relevant compliance contexts
- **Remediation Generator**: Synthesizes Ansible playbooks from retrieved knowledge and drift specifications using LLM capabilities
- **Failure Rewriter**: Analyzes execution failures and generates alternative remediation approaches when initial attempts fail

**Design Rationale**: LLM capabilities are deliberately restricted to remediation synthesis to maintain deterministic verification integrity. AI involvement is confined to the creative generation phase, ensuring that compliance validation remains objective and reproducible.

### Control Layer

**Responsibilities**:
- **Orchestrator**: Coordinates workflow execution across layers and manages state transitions
- **Retry Controller**: Implements controlled retry logic with convergence guarantees
- **State Manager**: Maintains system state and ensures atomic transitions between compliance states

## 4. Compliance State Machine Model

### Formal State Definition

The framework implements a finite state machine with the following states:

- **Compliant**: System state matches all compliance requirements
- **Drift Detected**: Deterministic auditing identifies specific compliance drifts
- **Remediation Generated**: AI layer produces remediation playbook based on drift analysis
- **Execution Failed**: Ansible playbook execution encounters errors
- **Verification Failed**: Post-remediation verification detects residual drifts
- **Remediation Succeeded**: Verification confirms compliance restoration
- **Unresolved**: System reaches maximum retry attempts without achieving compliance

### State Transitions and Convergence Guarantees

```
Compliant → Drift Detected (via scheduled/demand audit)
Drift Detected → Remediation Generated (via RAG + LLM generation)
Remediation Generated → Execution Failed (via Ansible failure)
Remediation Generated → Verification Failed (via post-execution drift detection)
Execution Failed → Remediation Generated (via failure analysis + rewrite, if retries < max)
Verification Failed → Remediation Generated (via residual drift analysis + rewrite, if retries < max)
Verification Failed → Unresolved (when retries >= max)
Execution Failed → Unresolved (when retries >= max)
Remediation Generated → Remediation Succeeded (via successful verification)
```

**Retry Limits and Loop Prevention**: Maximum retry count (default: 3) prevents infinite remediation cycles. Each retry incorporates failure analysis to ensure progressive improvement rather than repetitive failures. Convergence is guaranteed through monotonic compliance improvement requirements - each remediation cycle must reduce total drift count or achieve full compliance.

## 5. Controlled Self-Healing Logic

### Structured Retry Implementation

The redesigned retry logic incorporates:

- **max_retry_count**: Configurable upper bound on remediation attempts (default: 3)
- **structured error capture**: Categorized failure types (syntax errors, permission issues, dependency failures)
- **failure reason tracking**: Historical failure patterns to inform subsequent remediation generation
- **convergence stop condition**: Termination when drift count ceases to decrease or full compliance achieved

### Stability and Reproducibility Guarantees

This controlled approach ensures system stability by preventing resource exhaustion through bounded retry attempts. Reproducibility is maintained through deterministic failure categorization and structured error representation, enabling consistent experimental evaluation across different system configurations and failure scenarios.

## 6. Experimental Evaluation Framework

### Measurable Metrics

- **Initial Compliance Rate**: Percentage of rules passing pre-remediation audit
- **Autonomous Remediation Success Rate**: Percentage of drifts successfully resolved through AI-generated remediation
- **Average Retry Count**: Mean number of remediation attempts per rule violation
- **Convergence Time**: Time from drift detection to compliance achievement or failure
- **Comparison with Manual Remediation**: Performance metrics against human expert remediation approaches
- **RAG Ablation Impact**: Performance comparison with and without retrieval-augmented generation

### Validation Objectives

**Closed-Loop Effectiveness**: Metrics demonstrate the framework's ability to achieve full compliance restoration through iterative remediation and verification.

**Deterministic Verification Reliability**: Consistent audit results across multiple runs validate the deterministic nature of compliance assessment.

**AI Remediation Usefulness**: Success rate and retry count metrics quantify the value of LLM-generated remediation compared to rule-based approaches.

## 7. Research Contributions

This thesis presents a drift-aware compliance modeling framework that advances the state-of-the-art in autonomous security remediation through:

- **Drift-Aware Compliance Modeling**: Structured representation of compliance deviations enables precise, targeted remediation rather than blanket policy enforcement.

- **Deterministic Closed-Loop Verification**: Rigorous separation of AI-driven generation from deterministic validation ensures scientific validity and experimental reproducibility.

- **Controlled AI-Assisted Remediation**: Bounded retry mechanisms and failure analysis prevent instability while harnessing LLM capabilities for creative problem-solving.

- **Retrieval-Constrained Generation**: RAG integration ensures remediation synthesis is grounded in authoritative security knowledge, reducing hallucination risks and improving solution quality.

The framework demonstrates that autonomous compliance remediation can achieve both practical effectiveness and theoretical rigor, bridging the gap between AI-driven automation and deterministic system assurance.
