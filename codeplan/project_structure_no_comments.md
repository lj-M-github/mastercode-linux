# Project Structure (No Comments)

```text
project/
├── src/
│   ├── preprocessing/
│   │   ├── pdf_parser.py
│   │   ├── text_cleaner.py
│   │   └── chunker.py
│   ├── vector_db/
│   │   ├── chroma_client.py
│   │   ├── embedding.py
│   │   └── persistence.py
│   ├── rag/
│   │   ├── retriever.py
│   │   ├── ranker.py
│   │   └── knowledge_store.py
│   ├── llm/
│   │   ├── llm_client.py
│   │   └── prompt_templates.py
│   ├── executor/
│   │   ├── ansible_runner.py
│   │   ├── playbook_builder.py
│   │   └── ssh_client.py
│   ├── feedback/
│   │   ├── result_parser.py
│   │   ├── error_analyzer.py
│   │   └── self_heal.py
│   ├── reporting/
│   │   ├── report_generator.py
│   │   └── audit_log.py
│   └── main_agent.py
├── data/
│   ├── policies/
│   │   ├── cis/
│   │   ├── nist/
│   │   └── stig/
│   ├── corpus/
│   ├── knowledge_base/
│   └── test_results/
├── ansible_playbooks/
├── configs/
│   ├── config.yaml
│   ├── api_keys.example.yaml
│   └── model_selector.yaml
├── docs/
│   ├── architecture.md
│   ├── api_spec.md
│   └── runbook.md
├── tests/
│   ├── unit/
│   ├── integration/
│   └── data/
└── requirements.txt
```