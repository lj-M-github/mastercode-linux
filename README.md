<<<<<<< HEAD
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
=======
# 智能化系统动态安全加固框架

> 基于大语言模型与 RAG 技术的智能化系统动态安全加固框架研究

**毕业设计项目** | **版本**: 2.0 | **最后更新**: 2026-03-15

---

## 📖 项目简介

本项目实现了一个从非结构化 PDF 安全政策文档到可执行 Ansible 脚本的自动化转换框架，具备闭环自愈能力。通过结合 RAG（检索增强生成）技术和大语言模型，实现智能化的系统安全加固。

### 核心功能

- 📄 **PDF 文档解析** - 自动提取 CIS、NIST、STIG 等安全基准文档内容
- 🔍 **语义检索** - 基于向量数据库的智能知识检索
- 🤖 **代码生成** - 使用 LLM 将安全策略转换为 Ansible Playbook
- ⚙️ **自动化执行** - 通过 Ansible 执行安全加固
- 🔄 **自愈能力** - 执行失败时自动分析错误并重试
- 📊 **报告生成** - 自动生成审计报告和执行日志

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Hardening Framework                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Preprocessing│───▶│   Vector DB  │───▶│      RAG     │      │
│  │ - PDF Parser │    │ - ChromaDB   │    │ - Retriever  │      │
│  │ - Cleaner    │    │ - Embedding  │    │ - Ranker     │      │
│  │ - Chunker    │    │ - Persistence│    │ - Store      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                            │                    │               │
│                            ▼                    ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │     LLM      │◀───│  Main Agent  │───▶│   Executor   │      │
│  │ - Client     │    │ - Orchestrate│    │ - Ansible    │      │
│  │ - Prompts    │    │ - Decision   │    │ - SSH        │      │
│  └──────────────┘    └──────────────┘    │ - Builder    │      │
│                            │              └──────────────┘      │
│                            ▼                    │               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Feedback   │◀───│   Reporting  │◀───│   Result     │      │
│  │ - Parser     │    │ - Generator  │    │              │      │
│  │ - Analyzer   │    │ - Audit Log  │    │              │      │
│  │ - SelfHeal   │    │              │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 架构分层

| 层级 | 模块 | 职责 |
|------|------|------|
| **仓库层** | Preprocessing + Vector DB + RAG | 知识提取、存储与检索 |
| **大脑层** | LLM + Main Agent | 代码生成、决策编排 |
| **双手层** | Executor | Ansible 执行与 SSH 操作 |
| **反馈层** | Feedback + Reporting | 错误分析、自愈、报告生成 |

---

## 📁 项目结构

```
project/
├── src/
│   ├── preprocessing/         # PDF 解析、文本清洗、分块
│   ├── vector_db/             # ChromaDB 向量数据库
│   ├── rag/                   # 检索增强生成模块
│   ├── llm/                   # LLM 客户端和提示词模板
│   ├── executor/              # Ansible 执行器和 SSH 客户端
│   ├── feedback/              # 错误分析和自愈模块
│   ├── reporting/             # 报告生成和审计日志
│   └── main_agent.py          # 主代理编排器
├── data/
│   ├── policies/              # CIS、NIST、STIG 基准文件
│   ├── corpus/                # 语料库
│   └── knowledge_base/        # 知识库
├── configs/
│   ├── config.yaml            # 主配置文件
│   ├── api_keys.example.yaml  # API 密钥模板
│   └── model_selector.yaml    # 模型选择配置
├── docs/                      # 文档目录
├── tests/                     # 测试目录
├── examples/                  # 使用示例
└── requirements.txt           # Python 依赖
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js (可选，用于某些嵌入模型)

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

1. 复制配置文件模板：

```bash
cp configs/api_keys.example.yaml configs/api_keys.yaml
cp .env.example .env
```

2. 编辑配置文件，填入你的 API 密钥和其他设置。

### 基本使用

```python
from src.main_agent import SecurityHardeningAgent

# 初始化代理
agent = SecurityHardeningAgent(config_path="./configs/config.yaml")

# 知识入库
agent.ingest_knowledge("./data/policies/cis")

# 搜索知识
results = agent.search_knowledge("SSH configuration")

# 执行加固
result = agent.harden("SSH 配置", target_host="localhost")

# 生成报告
report_path = agent.generate_report("security_audit")
```

---

## 📦 模块说明

### 1. Preprocessing (`src/preprocessing/`)

| 文件 | 功能 |
|------|------|
| `pdf_parser.py` | 从 PDF 文档中提取文本 |
| `text_cleaner.py` | 清洗和规范化文本 |
| `chunker.py` | 将文本切分为适合向量化的块 |

### 2. Vector DB (`src/vector_db/`)

| 文件 | 功能 |
|------|------|
| `chroma_client.py` | ChromaDB 客户端 |
| `embedding.py` | 文本嵌入生成 |
| `persistence.py` | 数据持久化管理 |

### 3. RAG (`src/rag/`)

| 文件 | 功能 |
|------|------|
| `retriever.py` | 向量相似度检索 |
| `ranker.py` | 结果重排序 |
| `knowledge_store.py` | 统一知识存储接口 |

### 4. LLM (`src/llm/`)

| 文件 | 功能 |
|------|------|
| `llm_client.py` | LLM API 客户端 |
| `prompt_templates.py` | 提示词模板管理 |

### 5. Executor (`src/executor/`)

| 文件 | 功能 |
|------|------|
| `ansible_runner.py` | Ansible Playbook 执行 |
| `playbook_builder.py` | 动态构建 Playbook |
| `ssh_client.py` | SSH 连接与命令执行 |

### 6. Feedback (`src/feedback/`)

| 文件 | 功能 |
|------|------|
| `result_parser.py` | 解析执行结果 |
| `error_analyzer.py` | 分析错误原因 |
| `self_heal.py` | 自动修复逻辑 |

### 7. Reporting (`src/reporting/`)

| 文件 | 功能 |
|------|------|
| `report_generator.py` | 生成各类报告 |
| `audit_log.py` | 审计日志记录 |

---

## 🧪 测试

```bash
# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行所有测试并生成覆盖率报告
pytest --cov=src tests/
```

---

## 📊 性能指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| 知识检索准确率 | 检索结果相关性 | > 90% |
| 代码生成准确率 | 生成的 Ansible 代码可直接执行比例 | > 85% |
| 自愈成功率 | 失败任务经自愈后成功比例 | > 70% |
| 平均响应时间 | 从查询到生成 Playbook 的时间 | < 30s |
| 加固覆盖率 | 可自动化的安全基线比例 | > 80% |

---

## 🔒 安全准则

1. **API 密钥管理**: 所有 API 密钥必须通过环境变量或配置文件读取，禁止硬编码
2. **最小权限原则**: Ansible Playbook 应以最小必要权限执行
3. **审计追踪**: 所有操作必须记录到审计日志
4. **防御性设计**: 自愈重试上限为 3 次，防止无限循环

---

## 📚 文档

| 文档 | 路径 |
|------|------|
| 完整项目规范 | [Full_Project_Spec.md](Full_Project_Spec.md) |
| 架构文档 | [docs/architecture.md](docs/architecture.md) |
| API 规范 | [docs/api_spec.md](docs/api_spec.md) |
| 运行手册 | [docs/runbook.md](docs/runbook.md) |
| 安全基线文档 | [doc/README.md](doc/README.md) |

---

## 🛠 技术栈

- **向量数据库**: ChromaDB
- **嵌入模型**: Sentence Transformers (all-MiniLM-L6-v2)
- **LLM**: OpenAI GPT 系列
- **执行引擎**: Ansible
- **PDF 处理**: PyPDF, LangChain
- **数据验证**: Pydantic

---

## 👨‍💻 开发

```bash
# 代码格式化
black src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/
```

---

## 📝 毕业设计信息

- **作者**: MOU LINGJIE
- **课题**: 基于大语言模型与 RAG 技术的智能化系统动态安全加固框架研究
- **核心目标**: 实现从非结构化 PDF 政策到可执行 Ansible 脚本的自动化转换，并具备闭环自愈能力
- **版本**: 2.0 (重构后)

---

## 📄 许可证

本项目为毕业设计作品，仅供学术参考。
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
