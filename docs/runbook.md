# Runbook

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy API keys template
cp configs/api_keys.example.yaml configs/api_keys.yaml
# Edit configs/api_keys.yaml with your actual API keys
```

### 2. Configuration

Edit `configs/config.yaml` to customize settings:

```yaml
db:
  path: ./vector_db
  collection_name: cloud_security_benchmarks

llm:
  model: deepseek-chat
  temperature: 0.1
```

### 3. Knowledge Ingestion

```python
from src.main_agent import SecurityHardeningAgent

agent = SecurityHardeningAgent()

# Ingest PDF documents
report = agent.ingest_knowledge("./doc")
print(f"Ingested {report['items_added']} items")
```

### 4. Search Knowledge

```python
# Search for SSH-related rules
results = agent.search_knowledge("SSH configuration", n_results=5)

for result in results:
    print(f"Rule {result['metadata']['rule_id']}: {result['metadata']['section_title']}")
```

### 5. Generate Playbook

```python
playbook = agent.generate_playbook(
    rule_id="1.1",
    section_title="Ensure SSH root login is disabled",
    remediation="Set PermitRootLogin to no in sshd_config",
    cloud_provider="alibaba"
)
print(playbook)
```

### 6. Execute Hardening

```python
# Execute with self-healing enabled
result = agent.harden("SSH configuration", target_host="localhost", enable_self_heal=True)

if result['success']:
    print("Hardening completed successfully")
else:
    print(f"Hardening failed: {result}")
```

### 7. Generate Report

```python
report_path = agent.generate_report("security_audit")
print(f"Report saved to: {report_path}")
```

## Troubleshooting

### Issue: Vector DB Not Found

**Error**: `Collection not found`

**Solution**:
1. Run knowledge ingestion first
2. Check `vector_db` directory exists

### Issue: LLM API Error

**Error**: `DeepSeek API call failed`

**Solution**:
1. Verify API key in `configs/api_keys.yaml` or set `DEEPSEEK_API_KEY` env var
2. Check network connection to https://api.deepseek.com
3. Use mock mode for testing (no API key needed)

### Issue: Ansible Execution Failed

**Error**: `ansible-playbook command not found`

**Solution**:
1. Install Ansible: `pip install ansible`
2. Or use WSL/Docker for Linux environment

### Issue: Self-Healing Not Working

**Error**: `Healing failed after max retries`

**Solution**:
1. Increase `max_retries` in config
2. Check LLM is available
3. Review error logs in `audit_logs/`

## Common Commands

```bash
# Run knowledge ingestion
python -c "from src.main_agent import SecurityHardeningAgent; a = SecurityHardeningAgent(); a.ingest_knowledge('./doc')"

# Search knowledge
python -c "from src.main_agent import SecurityHardeningAgent; a = SecurityHardeningAgent(); print(a.search_knowledge('SSH'))"

# View stats
python -c "from src.main_agent import SecurityHardeningAgent; a = SecurityHardeningAgent(); print(a.get_stats())"
```

## Directory Structure

```
project/
├── configs/           # Configuration files
├── data/
│   └── policies/cis   # Policy documents
├── doc/               # Input PDF documents
├── playbooks/         # Generated Ansible playbooks
├── reports/           # Generated reports
├── audit_logs/        # Audit logs
├── vector_db/         # Vector database
└── src/               # Source code
```

## Best Practices

1. **Backup Vector DB**: Regularly backup `vector_db/` directory
2. **Review Playbooks**: Always review generated playbooks before execution
3. **Test Mode**: Use `enable_self_heal=False` for initial testing
4. **Logging**: Check `audit_logs/` for detailed operation history
5. **Rate Limits**: Be mindful of LLM API rate limits
