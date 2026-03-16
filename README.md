# Security Hardening Framework with RAG and LLM

A framework for automated security hardening using Retrieval-Augmented Generation (RAG) and Large Language Models (LLM). The system ingests security benchmark documents (PDFs), processes them through a RAG pipeline, and uses an intelligent agent to generate and execute hardening actions via Ansible.

## Architecture Overview

```
├── data/raw/              # Raw PDF benchmark documents
├── src/ingestion/         # RAG data ingestion and vector storage
├── src/agent/            # Core reasoning engine (Brain)
├── src/executor/         # Ansible execution and feedback (Hands)
└── tests/                # Experimental test scripts
```

### Component Description

1. **Ingestion Pipeline** (`src/ingestion/`): Processes PDF documents, extracts text, chunks content, and stores embeddings in a vector database for retrieval.

2. **Agent Engine** (`src/agent/`): The "Brain" that uses LLM for reasoning. It queries the RAG system for relevant security benchmarks, analyzes the current system state, and generates actionable hardening steps.

3. **Executor** (`src/executor/`): The "Hands" that executes hardening actions via Ansible playbooks. It also collects feedback from execution results to improve future decisions.

4. **Raw Data** (`data/raw/`): Contains security benchmark PDFs (e.g., CIS benchmarks, NIST guidelines).

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd security-hardening-framework
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   VECTOR_DB_PATH=./data/vectordb
   ANSIBLE_INVENTORY=./inventory.ini
   ```

## Usage

### 1. Ingest Security Documents

Place PDF benchmark files in `data/raw/`, then run the ingestion pipeline:

```python
from src.ingestion.pdf_processor import PDFProcessor
from src.ingestion.vector_store import VectorStore

processor = PDFProcessor()
chunks = processor.process_directory("data/raw/")
vector_store = VectorStore()
vector_store.add_documents(chunks)
```

### 2. Query the RAG System

```python
from src.agent.rag_querier import RAGQuerier

querier = RAGQuerier()
results = querier.query("Windows Server 2019 CIS benchmark for authentication")
```

### 3. Run the Security Hardening Agent

```python
from src.agent.hardening_agent import HardeningAgent

agent = HardeningAgent()
plan = agent.generate_hardening_plan(target_system="web_server")
```

### 4. Execute Hardening Actions

```python
from src.executor.ansible_runner import AnsibleRunner

runner = AnsibleRunner()
result = runner.execute_playbook(playbook_path="hardening_playbook.yml")
```

## Development

### Project Structure

- `src/ingestion/`: PDF parsing, text chunking, embedding generation, vector DB operations.
- `src/agent/`: LLM integration, prompt engineering, reasoning logic, RAG query interface.
- `src/executor/`: Ansible playbook generation, execution, result parsing, feedback collection.
- `tests/`: Unit and integration tests for all components.

### Adding New Security Benchmarks

1. Place new PDF files in `data/raw/`.
2. The ingestion pipeline will automatically process them during the next run.
3. Ensure the PDFs are text-based (not scanned images) for optimal extraction.

### Extending the Framework

- **New Document Types**: Implement additional parsers in `src/ingestion/parsers/`.
- **New Vector Databases**: Extend `VectorStore` class to support other vector DBs.
- **Alternative Executors**: Implement new executor classes for different automation tools (Terraform, Chef, etc.).

## Testing

Run the test suite:

```bash
pytest tests/
```

For specific module tests:
```bash
pytest tests/ingestion/
pytest tests/agent/
pytest tests/executor/
```

## Configuration

Configuration is managed via environment variables and YAML files:

- `.env`: API keys and sensitive data.
- `config/ingestion.yaml`: Chunk size, overlap, embedding model settings.
- `config/agent.yaml`: LLM model selection, temperature, max tokens.
- `config/executor.yaml`: Ansible connection parameters, timeout settings.

## Roadmap

- [ ] PDF ingestion pipeline with chunking and embeddings
- [ ] Vector database integration (ChromaDB)
- [ ] LLM agent with RAG query capabilities
- [ ] Ansible playbook generation from agent decisions
- [ ] Execution feedback loop for continuous improvement
- [ ] Web UI for monitoring and control
- [ ] Multi‑platform support (Linux, Windows, cloud)

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m 'Add some feature'`.
4. Push to the branch: `git push origin feature/your-feature`.
5. Open a pull request.

## License

MIT License. See `LICENSE` file for details.

## Acknowledgments

- Built with [LangChain](https://www.langchain.com/) and [ChromaDB](https://www.trychroma.com/).
- Inspired by security automation frameworks and RAG‑based AI systems.