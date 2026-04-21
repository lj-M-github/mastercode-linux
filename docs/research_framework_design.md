# LLM-Driven Autonomous Compliance Remediation Framework
## Research Architecture Design Document

---

## 1. Drift Model Design

### 1.1 Conceptual Definition

**Compliance Drift** is defined as the structured deviation between the expected configuration state (per security benchmark specification) and the actual observed state on the target system.

Traditional compliance auditing employs a binary classification model:
```
is_compliant ∈ {True, False}
```

This abstraction is insufficient for autonomous remediation because:
- It provides no actionable information for remediation synthesis
- It collapses heterogeneous configuration discrepancies into a single boolean flag
- It prevents granular verification of partial remediation success

### 1.2 Structured Drift Representation

We propose a **Drift-Aware Compliance Model** that replaces boolean pass/fail with explicit drift field representation:

```python
@dataclass
class DriftField:
    """Single configuration deviation."""
    key: str              # Configuration parameter name
    expected: str         # Benchmark-specified value
    actual: str           # Observed system value
    comparison_type: str  # Matching operator: regex_match | exact | contains | not_contains

@dataclass
class DriftResult:
    """Structured compliance drift report."""
    rule_id: str
    title: str
    is_compliant: bool
    drifts: List[DriftField]  # Empty iff is_compliant=True
    check_command: str
    actual_output: str
    severity: str
    domain: str
```

### 1.3 Theoretical Justification

**Why Drift Modeling is Necessary:**

1. **Remediation Precision**: LLM-based remediation requires concrete configuration deltas as input. A drift field `(key=PermitRootLogin, expected=no, actual=yes)` directly maps to the remediation action `Set PermitRootLogin=no`. Binary compliance cannot provide this mapping.

2. **Verification Completeness**: Post-execution verification must confirm that each drifted field has been corrected. With explicit drift representation, verification becomes a field-level comparison rather than rule-level re-execution.

3. **Partial Success Handling**: A remediation may correct 3 of 5 drifted fields. Binary models cannot represent this intermediate state. Drift-aware models support incremental convergence tracking.

**How Drift Improves Remediation Precision:**

| Input Type | Remediation Quality |
|------------|---------------------|
| Boolean: "Rule 5.2.1 failed" | LLM must infer the problem → ambiguity, hallucination risk |
| Drift: `[(PermitRootLogin, expected=no, actual=yes)]` | LLM receives exact transformation → deterministic remediation |

**How Drift Strengthens Closed-Loop Verification:**

```
Pre-remediation drift:  D₀ = {f₁, f₂, f₃}
Post-remediation drift: D₁ = {f₂}  (f₁, f₃ corrected)
Verification: D₁ ⊆ D₀ ∧ |D₁| < |D₀| → partial success, continue retry
```

The verification engine can now perform **delta analysis** rather than blind re-execution.

---

## 2. Layered Architecture Separation

### 2.1 Three-Layer Model

We define a strict separation of concerns across three architectural layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTROL LAYER                             │
│  Orchestrator │ Retry Controller │ State Manager             │
│  (Deterministic coordination, no AI inference)               │
├─────────────────────────────────────────────────────────────┤
│                      AI LAYER                                │
│  RAG Retrieval │ Remediation Generator │ Failure Rewriter    │
│  (LLM-based synthesis, constrained by deterministic context) │
├─────────────────────────────────────────────────────────────┤
│                  DETERMINISTIC LAYER                         │
│  Rule Loader │ Compliance Auditor │ Drift Detector           │
│  │ Verification Engine                                        │
│  (Shell commands, regex parsing, state comparison)           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Deterministic Layer

**Components:**

| Component | Responsibility | Implementation |
|-----------|---------------|----------------|
| Rule Loader | Parse YAML compliance specifications into structured rules | `cis_rhel9_checks.yaml` → `ComplianceRule` objects |
| Compliance Auditor | Execute `check_command` on target system | Subprocess/SSH execution |
| Drift Detector | Parse command output, compare against `expected_pattern` | Regex matching, field extraction |
| Verification Engine | Compare pre/post drift states, compute convergence delta | Set comparison on DriftField |

**Key Principle: No AI Inference in Deterministic Layer**

All operations are:
- Shell command execution (observable, reproducible)
- Regex pattern matching (mathematically defined)
- String comparison (exact, no ambiguity)

**Why Audit and Verification Must Remain Deterministic:**

1. **Reproducibility**: Compliance auditing must produce identical results across repeated executions. LLM outputs are stochastic; audit results must be deterministic.

2. **Trust**: Security compliance verification cannot tolerate hallucination. A false-positive "compliant" verdict is a security breach. Deterministic verification eliminates this risk.

3. **Ground Truth**: The deterministic layer provides the objective ground truth against which AI-generated remediations are evaluated. Without deterministic ground truth, the system has no verifiable success criterion.

### 2.3 AI Layer

**Components:**

| Component | Responsibility | Constraints |
|-----------|---------------|-------------|
| RAG Retrieval | Retrieve relevant remediation context from knowledge base | Vector search + graph traversal, no LLM |
| Remediation Generator | Synthesize Ansible playbook from drift + retrieved context | Input: DriftResult + Rule text. Output: YAML playbook |
| Failure Rewriter | Analyze execution error, rewrite playbook for retry | Input: Error log + drift. Output: Corrected playbook |

**Key Principle: LLM Restricted to Remediation Synthesis Only**

The LLM is never permitted to:
- Determine compliance status (reserved for Deterministic Layer)
- Execute commands directly (reserved for Ansible executor)
- Modify audit specifications (reserved for Rule Loader)
- Decide retry policy (reserved for Control Layer)

**Why LLM Must Be Restricted:**

1. **Safety Boundary**: LLMs can hallucinate incorrect compliance verdicts. Restricting LLM to remediation synthesis ensures that all compliance decisions are made by deterministic code.

2. **Verifiability**: LLM-generated playbooks are verified by deterministic drift audit. If the LLM produces incorrect remediation, verification detects the residual drift and triggers retry.

3. **Accountability**: Each layer has a single responsibility. Mixing AI inference with audit logic creates untraceable failure modes.

### 2.4 Control Layer

**Components:**

| Component | Responsibility |
|-----------|---------------|
| Orchestrator | Coordinate sequential execution: Audit → Generate → Execute → Verify |
| Retry Controller | Manage retry loop: max_retries, backoff, stop conditions |
| State Manager | Track compliance state transitions, persist knowledge on success |

**Key Principle: Deterministic Coordination**

The Control Layer:
- Executes pre-defined state machine transitions (no AI decision)
- Enforces retry limits (prevents infinite loops)
- Only stores successful remediations (prevents knowledge pollution)

---

## 3. Compliance State Machine Model

### 3.1 State Definitions

```
States:
  S₀: COMPLIANT              — Initial drift audit shows no deviation
  S₁: DRIFT_DETECTED         — DriftResult.drifts ≠ ∅
  S₂: REMEDIATION_GENERATED  — Playbook synthesized from drift
  S₃: EXECUTION_FAILED       — Ansible execution returned error
  S₄: VERIFICATION_FAILED    — Post-execution drift ≠ pre-execution drift
  S₅: REMEDIATION_SUCCEEDED  — Post-execution drift = ∅
  S₆: UNRESOLVED             — Max retries exhausted, residual drift persists
```

### 3.2 State Transition Diagram

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │ audit
              ┌────────────┴────────────┐
              │                         │
         drift=∅                    drift≠∅
              │                         │
              ▼                         ▼
        ┌───────────┐           ┌──────────────┐
        │ COMPLIANT │           │ DRIFT_DETECTED│
        │   (S₀)    │           │    (S₁)       │
        └─────┬─────┘           └───────┬───────┘
              │                         │ generate
              ▼                         ▼
           [DONE]              ┌───────────────────┐
                              │ REMEDIATION_GENERATED│
                              │      (S₂)           │
                              └───────┬─────────────┘
                                      │ execute
                         ┌────────────┴────────────┐
                         │                         │
                    success                    failure
                         │                         │
                         ▼                         ▼
              ┌──────────────────┐      ┌─────────────────┐
              │ verify post-drift │      │ EXECUTION_FAILED│
              └───────┬───────────┘      │     (S₃)        │
                      │                  └───────┬─────────┘
         ┌────────────┴────────────┐             │
         │                         │             │ self-heal
    drift=∅                    drift≠∅           │ (retry < max)
         │                         │             │
         ▼                         ▼             │
 ┌───────────────────┐  ┌─────────────────┐     │
 │REMEDIATION_SUCCEEDED│ │VERIFICATION_FAILED│◄──┘
 │      (S₅)         │  │     (S₄)        │
 └───────┬───────────┘  └───────┬─────────┘
         │                       │
         ▼                       │ self-heal
      [DONE]                     │ (retry < max)
                                 │
                                 └──────────────► S₂ (loop)

                                 ┌───────────────┐
                                 │  UNRESOLVED   │
                                 │    (S₆)       │
                                 │ retry=max     │
                                 └───────────────┘
```

### 3.3 Formal Transition Rules

```
T₁: START → S₀ (COMPLIANT)        iff DriftResult.is_compliant = True
T₂: START → S₁ (DRIFT_DETECTED)   iff DriftResult.is_compliant = False

T₃: S₁ → S₂ (REMEDIATION_GENERATED)  action: generate_playbook_from_drift()

T₄: S₂ → S₅ (REMEDIATION_SUCCEEDED)  iff execute()=success ∧ post_audit.is_compliant=True
T₅: S₂ → S₃ (EXECUTION_FAILED)       iff execute()=failure
T₆: S₂ → S₄ (VERIFICATION_FAILED)    iff execute()=success ∧ post_audit.is_compliant=False

T₇: S₃ → S₂ (loop)  iff retry_count < max_retries  action: self_heal()
T₈: S₃ → S₆ (UNRESOLVED)  iff retry_count = max_retries

T₉: S₄ → S₂ (loop)  iff retry_count < max_retries  action: self_heal()
T₁₀: S₄ → S₆ (UNRESOLVED)  iff retry_count = max_retries
```

### 3.4 Convergence Guarantee

**Theorem**: The state machine terminates in finite time.

**Proof**:
- Each cycle through S₂→S₃→S₂ or S₂→S₄→S₂ increments `retry_count` by 1
- Transitions T₇, T₉ have guard `retry_count < max_retries`
- Transitions T₈, T₁₀ have guard `retry_count = max_retries`
- After `max_retries` iterations, the guard forces transition to S₆ (terminal state)
- States S₀, S₅, S₆ are terminal (no outgoing transitions)
- Therefore, the machine reaches a terminal state within `max_retries + 2` transitions

**Infinite Loop Prevention**:
1. Counter-based termination guard
2. Terminal states have no outgoing edges
3. Backoff delays prevent rapid retry cycling

---

## 4. Controlled Self-Healing Logic

### 4.1 Retry Control Parameters

```python
@dataclass
class RetryConfig:
    max_retries: int = 3           # Upper bound on retry iterations
    base_delay: float = 0.5        # Exponential backoff base (seconds)
    max_delay: float = 30.0        # Backoff ceiling
    retryable_errors: Set[str]     # Error categories eligible for retry
```

### 4.2 Structured Error Capture

```python
@dataclass
class ExecutionError:
    category: str          # syntax | connection | permission | command_not_found | logic
    severity: str          # low | medium | high | critical
    root_cause: str        # Extracted from Ansible output
    suggestions: List[str] # LLM-generated remediation hints
    raw_output: str        # Full Ansible stderr/stdout
```

### 4.3 Healing Procedure

```python
def heal(original_playbook: str, error: ExecutionError, drift: DriftResult,
         retry_count: int, config: RetryConfig) -> HealingResult:

    # Guard: Stop condition
    if retry_count >= config.max_retries:
        return HealingResult(
            success=False,
            failure_reason="max_retries_exceeded",
            attempts=retry_count
        )

    # Guard: Non-retryable error
    if error.category not in config.retryable_errors:
        return HealingResult(
            success=False,
            failure_reason=f"non_retryable:{error.category}",
            attempts=retry_count
        )

    # Backoff delay
    delay = min(config.base_delay * 2**(retry_count-1), config.max_delay)
    time.sleep(delay)

    # AI Layer: Rewrite playbook
    rewritten = llm_rewrite(
        playbook=original_playbook,
        error_context=error,
        drift_context=drift  # Constrain LLM by drift, not free-form
    )

    # Deterministic Layer: Execute
    exec_result = execute(rewritten)

    # Deterministic Layer: Verify
    post_drift = audit_drift(drift.rule_id)

    # Convergence check
    if post_drift.is_compliant:
        return HealingResult(success=True, rewritten_playbook=rewritten, attempts=retry_count+1)

    # Partial convergence check
    if len(post_drift.drifts) < len(drift.drifts):
        # Progress detected, continue retry with updated drift
        return heal(rewritten, exec_result.error, post_drift, retry_count+1, config)

    # No progress, continue retry
    return heal(rewritten, exec_result.error, post_drift, retry_count+1, config)
```

### 4.4 Stability and Reproducibility Guarantees

**Stability**:
- Counter guard prevents unbounded iteration
- Error category filter excludes hopeless failures (e.g., authentication)
- Backoff prevents resource exhaustion

**Reproducibility**:
- Deterministic audit provides identical drift across runs
- LLM input is constrained (drift + error, not free prompt)
- Knowledge consolidation only on verified success

---

## 5. Experimental Evaluation Framework

### 5.1 Primary Metrics

| Metric | Definition | Measurement |
|--------|------------|-------------|
| Initial Compliance Rate | `|{r: pre_audit(r).is_compliant}| / |rules|` | Pre-remediation audit ratio |
| Autonomous Remediation Success Rate | `|{r: final_state ∈ {S₀,S₅}}| / |drifted_rules|` | Terminal state distribution |
| Average Retry Count | `Σ retry_count(r) / |remediated_rules|` | Loop iteration count |
| Convergence Time | Wall-clock from S₁ to terminal state | Timestamp difference |
| Final Compliance Rate | `|{r: post_audit(r).is_compliant}| / |rules|` | Post-remediation audit ratio |

### 5.2 Comparative Metrics

| Comparison | Method |
|------------|--------|
| Manual vs Autonomous | Time-to-compliance: human expert vs automated agent |
| RAG vs No-RAG | Remediation success rate with/without knowledge retrieval |
| Drift-aware vs Binary | Retry count: explicit drift vs boolean compliance input |

### 5.3 Ablation Study Design

```
Baseline: Full framework (Deterministic + AI + Control + RAG + Drift)

Ablation 1: No-RAG
  - Disable knowledge retrieval
  - LLM generates playbook from rule text only (no context)
  - Hypothesis: Success rate drops, hallucination increases

Ablation 2: No-Drift
  - Replace DriftResult with boolean compliance flag
  - LLM must infer remediation from rule text + pass/fail
  - Hypothesis: Retry count increases, remediation precision drops

Ablation 3: No-Self-Heal
  - Disable retry loop (max_retries=0)
  - Single-shot remediation only
  - Hypothesis: Success rate drops significantly

Ablation 4: No-Verification
  - Disable post-execution audit
  - Accept Ansible success as final state
  - Hypothesis: False-positive compliance increases
```

### 5.4 Validation Framework

**Closed-Loop Effectiveness Validation**:
- Measure: Convergence rate from S₁ to S₅
- Criterion: >70% of drifted rules reach S₅ within max_retries

**Deterministic Verification Reliability**:
- Measure: Agreement between Ansible success and post_audit.is_compliant
- Criterion: No false-positive cases (Ansible success but drift persists)

**AI Remediation Usefulness**:
- Measure: First-shot success rate (retry_count=0)
- Criterion: >50% of drifted rules remediated without retry

---

## 6. Research Contribution Statement

### 6.1 Problem Statement

Existing compliance remediation systems suffer from three fundamental limitations:

1. **Binary Compliance Abstraction**: Traditional auditing collapses configuration deviations into boolean pass/fail flags, providing insufficient context for automated remediation.

2. **Unverified AI Remediation**: LLM-generated remediation scripts are executed without deterministic post-execution verification, creating false-positive compliance verdicts.

3. **Uncontrolled Retry Logic**: Self-healing mechanisms lack convergence guarantees, risking infinite loops and non-reproducible behavior.

### 6.2 Contributions

This thesis presents a **Drift-Aware Autonomous Compliance Remediation Framework** with four core contributions:

**C1: Drift-Aware Compliance Modeling**

We introduce a structured drift representation that replaces boolean compliance with explicit field-level deviation capture. Each drift field specifies the configuration key, expected value, actual value, and comparison operator. This abstraction enables:
- Precision input for LLM remediation synthesis
- Delta-based post-execution verification
- Partial convergence tracking across retry iterations

**C2: Deterministic Closed-Loop Verification**

We enforce a strict architectural separation where compliance auditing and verification remain entirely deterministic (shell commands, regex parsing). The AI layer (LLM) is restricted to remediation synthesis only and cannot influence compliance verdicts. This separation ensures:
- Reproducible audit results across repeated executions
- Zero tolerance for hallucinated compliance status
- Objective ground truth for remediation evaluation

**C3: Controlled AI-Assisted Remediation**

We design a self-healing mechanism with formal convergence guarantees. The retry controller operates on a state machine with bounded iteration, exponential backoff, and structured error capture. LLM inputs are constrained by drift context (not free-form prompts), preventing unconstrained hallucination.

**C4: Retrieval-Constrained Generation**

We integrate RAG-based knowledge retrieval into the remediation pipeline. The LLM receives retrieved rule context, structured drift, and target OS information as constrained inputs. This retrieval-constrained generation reduces hallucination risk and improves first-shot remediation accuracy.

### 6.3 Theoretical Framework

The system is modeled as a **Compliance State Machine** with six states and ten transitions. Each transition is guarded by deterministic conditions (drift equality, retry counter bounds). We prove that the state machine terminates in finite time, ensuring system stability.

### 6.4 Experimental Validation

We evaluate the framework against CIS RHEL9 benchmarks across five metrics:
- Retrieval accuracy (>90%)
- Remediation generation accuracy (>85%)
- Self-healing success rate (>70%)
- Response latency (<30s)
- Coverage (>80%)

Ablation studies validate the necessity of each architectural component (RAG, Drift-awareness, Self-healing, Verification).

### 6.5 Implementation Realization

The framework is implemented as a three-layer system:
- **Deterministic Layer**: YAML rule loader, drift auditor (regex-based), verification engine
- **AI Layer**: RAG retrieval (ChromaDB + hierarchical graph), LLM playbook generator (DeepSeek API)
- **Control Layer**: Retry orchestrator, state manager, knowledge consolidation

The implementation validates that:
- All compliance decisions are made by deterministic code
- LLM outputs are verified before acceptance
- Retry behavior is bounded and reproducible

---

## 7. Implementation Roadmap (1.5-Month Timeline)

| Week | Task | Deliverable |
|------|------|-------------|
| 1-2 | Drift Model Refinement | Structured DriftResult with field-level comparison |
| 2-3 | State Machine Implementation | Formal state transition logic with guards |
| 3-4 | Controlled Self-Healing | Retry controller with convergence tracking |
| 4-5 | Evaluation Framework | Benchmark test suite with ablation support |
| 5-6 | Experimental Runs | Metric collection, ablation studies |
| 6-7 | Thesis Writing | Architecture documentation, contribution statement |

---

## Appendix A: DriftResult Schema

```yaml
DriftResult:
  rule_id: string          # CIS rule identifier (e.g., "5.2.1")
  title: string            # Human-readable rule title
  is_compliant: boolean    # True iff drifts is empty
  drifts:                  # List of DriftField objects
    - key: string          # Configuration parameter
      expected: string     # Benchmark value
      actual: string       # Observed value
      comparison_type: enum[regex_match, exact, contains, not_contains]
  check_command: string    # Shell command that produced actual_output
  actual_output: string    # Raw command output
  severity: enum[low, medium, high, critical]
  domain: string           # Security domain (Access, Network, etc.)
```

## Appendix B: State Machine Formalization

```
M = (S, T, G, A, s₀, F)

S = {S₀, S₁, S₂, S₃, S₄, S₅, S₆}           # States
T = {T₁, T₂, ..., T₁₀}                      # Transitions
G = {g₁: (retry < max), g₂: (drift=∅), ...}  # Guards
A = {audit, generate, execute, verify}      # Actions
s₀ = START                                   # Initial state
F = {S₀, S₅, S₆}                            # Terminal states
```