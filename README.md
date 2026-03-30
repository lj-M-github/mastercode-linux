# Security Hardening Framework with RAG and LLM

A framework for automated security hardening using Retrieval-Augmented Generation (RAG) and Large Language Models (LLM). The system ingests security benchmark content (PDF and YAML controls), retrieves relevant guidance, generates hardening actions, executes them with Ansible, and produces audit-ready reports.

## Architecture Overview

```
.
├── data/                  # Security policies, corpus, and benchmark data
├── configs/               # Runtime configuration and model/API settings
├── src/
│   ├── main_agent.py      # Central orchestration agent
│   ├── preprocessing/     # PDF parsing, cleaning, chunking
│   ├── rag/               # Knowledge store and retrieval/ranking
│   ├── llm/               # LLM client and prompt templates
│   ├── executor/          # Ansible playbook execution
│   ├── feedback/          # Self-healing and result analysis
│   ├── reporting/         # Reports and audit logs
│   └── vector_db/         # Embedding and persistence adapters
└── tests/                 # Unit and integration tests
```

## Core Components

1. Preprocessing (`src/preprocessing/`)
   - Parses benchmark documents and turns them into clean, chunked text.

2. Knowledge and Retrieval (`src/rag/`, `src/vector_db/`)
   - Stores benchmark knowledge in Chroma-based vector storage.
   - Performs semantic retrieval with ranking for better precision.

3. Agent Orchestration (`src/main_agent.py`, `src/llm/`)
   - Coordinates ingestion, retrieval, LLM prompting, hardening generation, and execution flow.

4. Execution and Feedback (`src/executor/`, `src/feedback/`)
   - Runs generated hardening logic using Ansible.
   - Parses failures and supports self-healing retries.

5. Reporting (`src/reporting/`)
   - Generates reports and writes audit logs for traceability.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mastercode-linux
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure API keys and model settings:
   - Copy and edit `configs/api_keys.example.yaml` as needed.
   - Update `configs/model_selector.yaml` and `configs/config.yaml` for your runtime.

## Quick Usage

### Python API

```python
from src.main_agent import SecurityHardeningAgent

config = {
    "db_path": "./vector_db",
    "model_name": "all-MiniLM-L6-v2",
    "llm_model": "deepseek-chat",
    "playbook_dir": "./playbooks",
    "report_dir": "./reports",
    "audit_dir": "./audit_logs",
}

agent = SecurityHardeningAgent(config)

# 1) Ingest benchmark knowledge
ingest_report = agent.ingest_knowledge("./data/policies/cis")

# 2) Search knowledge
results = agent.search_knowledge("SSH configuration", n_results=5)

# 3) Run hardening workflow
hardening_result = agent.harden(
    query="SSH security configuration",
    target_host="localhost",
    enable_self_heal=True,
)

# 4) Generate report
report_path = agent.generate_report("security_hardening_demo")
print(report_path)
```

### Example Script

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

Main configuration files:

- `configs/config.yaml`: Framework runtime settings.
- `configs/model_selector.yaml`: Model routing and selection.
- `configs/api_keys.yaml`: API keys (local only; do not commit secrets).

## Notes

- Ansible execution requires `ansible-playbook` to be installed and available in `PATH`.
- The vector database is stored under `./vector_db` by default.
- Generated reports and logs are written to `./reports` and `./audit_logs`.

## Contributing

1. Fork the repository.
2. Create a branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m "Add your feature"`.
4. Push: `git push origin feature/your-feature`.
5. Open a pull request.

## License

MIT License.
