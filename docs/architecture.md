# Architecture Documentation

## System Overview

The Security Hardening Framework is designed as a modular pipeline that transforms security policies into executable Ansible playbooks through an intelligent, self-healing process.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Hardening Framework                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Preprocessing│───▶│   Vector DB  │───▶│      RAG     │      │
│  │              │    │              │    │              │      │
│  │ - PDF Parser │    │ - ChromaDB   │    │ - Retriever  │      │
│  │ - Cleaner    │    │ - Embedding  │    │ - Ranker     │      │
│  │ - Chunker    │    │ - Persistence│    │ - Store      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                            │                    │               │
│                            ▼                    ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │     LLM      │◀───│  Main Agent  │───▶│   Executor   │      │
│  │              │    │              │    │              │      │
│  │ - Client     │    │ - Orchestrate│    │ - Ansible    │      │
│  │ - Prompts    │    │ - Decision   │    │ - SSH        │      │
│  └──────────────┘    └──────────────┘    │ - Builder    │      │
│                            │              └──────────────┘      │
│                            ▼                    │               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Feedback   │◀───│   Reporting  │◀───│   Result     │      │
│  │              │    │              │    │              │      │
│  │ - Parser     │    │ - Generator  │    │              │      │
│  │ - Analyzer   │    │ - Audit Log  │    │              │      │
│  │ - SelfHeal   │    │              │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### 1. Preprocessing (`src/preprocessing/`)
- **PDF Parser**: Extract text from PDF documents
- **Text Cleaner**: Remove noise and normalize extracted text
- **Chunker**: Split text into manageable chunks for vectorization

### 2. Vector DB (`src/vector_db/`)
- **Chroma Client**: Interface to ChromaDB vector database
- **Embedding Model**: Generate text embeddings using Sentence Transformers
- **Persistence**: Manage database state and backups

### 3. RAG (`src/rag/`)
- **Retriever**: Search for relevant documents using vector similarity
- **Ranker**: Re-rank and filter retrieval results
- **Knowledge Store**: Unified interface for knowledge management

### 4. LLM (`src/llm/`)
- **LLM Client**: Interface to OpenAI and other LLM providers
- **Prompt Templates**: Reusable prompt templates for various tasks

### 5. Executor (`src/executor/`)
- **Ansible Runner**: Execute Ansible playbooks
- **Playbook Builder**: Programmatically build Ansible playbooks
- **SSH Client**: SSH connection and command execution

### 6. Feedback (`src/feedback/`)
- **Result Parser**: Parse execution results
- **Error Analyzer**: Analyze execution errors and provide suggestions
- **Self Heal**: Automatic error recovery and playbook rewriting

### 7. Reporting (`src/reporting/`)
- **Report Generator**: Generate execution reports in various formats
- **Audit Log**: Record audit trail of all operations

### 8. Main Agent (`src/main_agent.py`)
Central orchestration agent that coordinates all modules.

## Data Flow

1. **Knowledge Ingestion**: PDF → Preprocessing → Vector DB
2. **Query Processing**: User Query → RAG → Retrieved Documents
3. **Code Generation**: Retrieved Docs → LLM → Ansible Playbook
4. **Execution**: Playbook → Executor → Results
5. **Feedback**: Results → Feedback → (Self-Heal if needed) → Report

## Configuration

All configuration files are located in `configs/`:
- `config.yaml`: Main configuration
- `api_keys.example.yaml`: API keys template
- `model_selector.yaml`: Model selection rules
