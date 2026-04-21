# Security Hardening Framework with RAG and LLM

A framework for automated security hardening using Retrieval-Augmented Generation (RAG) and Large Language Models (LLM). The system ingests security benchmark content (PDF and YAML controls), retrieves relevant guidance, generates Ansible hardening playbooks via LLM, executes them, self-heals on failure, audits the resulting system state against CIS rules, and produces audit-ready reports.

## Architecture Overview

```
.
├── data/
│   ├── compliance_checks/         # CIS rule check specifications (YAML)
│   │   └── cis_rhel9_checks.yaml  # 16 CIS RHEL 9 v2.0.0 rules with check commands
│   ├── policies/                  # CIS / NIST / STIG source documents
│   └── corpus/                    # Raw ingested data
├── configs/                       # Runtime configuration and model/API settings
├── src/
│   ├── main_agent.py              # Central orchestration agent
│   ├── preprocessing/             # PDF parsing, cleaning, chunking
│   ├── rag/                       # Knowledge store and retrieval/ranking
│   ├── llm/                       # LLM client and prompt templates
│   ├── executor/                  # Ansible playbook execution and SSH client
│   ├── feedback/                  # Self-healing and result analysis
│   ├── compliance/                # Post-execution compliance auditing
│   ├── reporting/                 # Reports and audit logs
│   └── vector_db/                 # Embedding and persistence adapters
└── tests/                         # Unit and integration tests
```

## Core Components

### 1. Preprocessing (`src/preprocessing/`)
Parses benchmark documents (PDF and YAML controls) and converts them into clean, chunked text with structured CIS rule metadata.

### 2. Knowledge and Retrieval (`src/rag/`, `src/vector_db/`)
Stores benchmark knowledge in a Chroma-based vector store. Supports semantic retrieval with ranking and optional cloud-provider filtering.

### 3. Agent Orchestration (`src/main_agent.py`, `src/llm/`)
`SecurityHardeningAgent` coordinates the full pipeline: ingestion → retrieval → LLM playbook generation → execution → self-healing → compliance audit → reporting.

### 4. Execution and Feedback (`src/executor/`, `src/feedback/`)
- Runs generated Ansible playbooks against the target host (local or SSH).
- Parses failures and retries with LLM-rewritten playbooks (self-healing loop, up to 3 attempts by default).

### 5. Compliance Auditing (`src/compliance/`)
`ComplianceAuditor` loads `data/compliance_checks/cis_rhel9_checks.yaml` and verifies actual system state by running check commands on the target host (via SSH or localhost) and matching output against expected regex patterns.

Covered domains across 16 CIS RHEL 9 v2.0.0 rules:

| Domain     | Rules             |
|------------|-------------------|
| SSH        | 5.2.1 – 5.2.5     |
| Filesystem | 6.1.1 – 6.1.4     |
| Kernel     | 3.1.1 – 3.2.1     |
| Audit      | 4.1.1 – 4.1.2     |
| Firewall   | 3.4.1 – 3.4.2     |

Each rule specifies:
- `check_command` — shell command run on the target host
- `expected_pattern` — regex that must match the command output for `pass`
- `remediation_hint` — concise fix guidance

### 6. Reporting (`src/reporting/`)
Generates Markdown reports and structured audit logs for traceability. Compliance failures are included as `compliance_fail` entries.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mastercode-linux
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure API keys and model settings:
   - Copy `configs/api_keys.example.yaml` to `configs/api_keys.yaml` and fill in keys.
   - Adjust `configs/model_selector.yaml` and `configs/config.yaml` for your runtime.

## Quick Usage

### Python API

```python
from src.main_agent import SecurityHardeningAgent
from src.compliance import ComplianceAuditor

config = {
    "db_path": "./vector_db",
    "model_name": "all-MiniLM-L6-v2",
    "llm_model": "deepseek-chat",
    "playbook_dir": "./playbooks",
    "report_dir": "./reports",
    "audit_dir": "./audit_logs",
}

agent = SecurityHardeningAgent(config)

# 1) Ingest benchmark knowledge (PDF + YAML controls)
agent.ingest_knowledge("./data/policies/cis")

# 2) Run hardening workflow with self-healing
result = agent.harden(
    query="SSH security configuration",
    target_host="localhost",
    enable_self_heal=True,
)
print(result)
# {'success': True, 'results': [...], 'total': 1}

# 3) Audit actual system state against CIS rules
audit = agent.audit_compliance(
    rule_ids=["5.2.1", "5.2.2", "5.2.3"],
    ssh_host="192.168.1.10",
    ssh_username="ansible",
    ssh_key_file="~/.ssh/id_rsa",
)
print(audit["summary"]["pass_rate_pct"])  # e.g. "66.7%"

# 4) Generate report
report_path = agent.generate_report("security_hardening_demo")
print(report_path)
```

### Standalone compliance audit

```python
from src.compliance import ComplianceAuditor
from src.executor.ssh_client import SSHClient, SSHConfig

client = SSHClient(SSHConfig(host="10.0.0.5", username="ec2-user", key_file="~/.ssh/id_rsa"))
auditor = ComplianceAuditor(
    "data/compliance_checks/cis_rhel9_checks.yaml",
    ssh_client=client,
)

results = auditor.audit_all()
summary = auditor.summary(results)
print(summary)
# {
#   'total': 16, 'pass_count': 12, 'fail_count': 3, 'skip_count': 1,
#   'pass_rate': 0.8, 'pass_rate_pct': '80.0%',
#   'by_domain': {'ssh': {'pass': 4, 'fail': 1, 'skip': 0}, ...},
#   'failed_rules': ['5.2.3', '6.1.2', '3.4.1']
# }
```

### Example script

```bash
python examples/basic_usage.py
```

## Testing

Run all tests:

```bash
pytest tests/
```

Run by test type:

```bash
pytest tests/unit/
pytest tests/integration/
```

Or use the helper script:

```bash
python tests/run_tests.py
```

## Configuration

| File | Purpose |
|------|---------|
| `configs/config.yaml` | Framework runtime settings |
| `configs/model_selector.yaml` | Model routing and selection |
| `configs/api_keys.yaml` | API keys (local only — do not commit) |
| `data/compliance_checks/cis_rhel9_checks.yaml` | CIS rule check specs |

## Notes

- Ansible execution requires `ansible-playbook` to be installed and available in `PATH`.
- The vector database is stored under `./vector_db` by default.
- Generated reports and logs are written to `./reports` and `./audit_logs`.
- `ComplianceAuditor` runs in **localhost mode** (subprocess) when no `ssh_client` is provided, making it safe for local development and testing.
- `sshd -T` is used for SSH rule checks — it reads the runtime effective configuration including `Include` directives, which is more accurate than grepping `sshd_config` directly.

## Contributing

1. Fork the repository.
2. Create a branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m "Add your feature"`.
4. Push: `git push origin feature/your-feature`.
5. Open a pull request.

## License

MIT License.
