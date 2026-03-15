# 毕业设计：智能化系统动态安全加固框架开发规范 (Full Project Spec)

**作者**: MOU LINGJIE
**课题**: 基于大语言模型与 RAG 技术的智能化系统动态安全加固框架研究
**核心目标**: 实现从非结构化 PDF 政策到可执行 Ansible 脚本的自动化转换，并具备闭环自愈能力
**重构日期**: 2026-03-14

---

## 🏗 整体架构 (Architecture)

### 架构图

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
│  │   Feedback   │◀──│   Reporting │◀───│   Result     │      │
│  │              │    │              │    │              │      │
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
| **仓库层 (Library)** | Preprocessing + Vector DB + RAG | 知识提取、存储与检索 |
| **大脑层 (Brain)** | LLM + Main Agent | 代码生成、决策编排 |
| **双手层 (Hands)** | Executor | Ansible 执行与 SSH 操作 |
| **反馈层 (Feedback)** | Feedback + Reporting | 错误分析、自愈、报告生成 |

---

## 📁 项目结构 (Project Structure)

```
project/
├── src/
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── pdf_parser.py        # PDF 文档解析
│   │   ├── text_cleaner.py      # 文本清洗与规范化
│   │   └── chunker.py           # 文本分块
│   ├── vector_db/
│   │   ├── __init__.py
│   │   ├── chroma_client.py     # ChromaDB 客户端
│   │   ├── embedding.py         # 嵌入模型管理
│   │   └── persistence.py       # 数据持久化
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── retriever.py         # 向量检索
│   │   ├── ranker.py            # 结果排序
│   │   └── knowledge_store.py   # 知识存储接口
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── llm_client.py        # LLM 客户端（OpenAI 等）
│   │   └── prompt_templates.py  # 提示词模板
│   ├── executor/
│   │   ├── __init__.py
│   │   ├── ansible_runner.py    # Ansible 执行器
│   │   ├── playbook_builder.py  # Playbook 构建器
│   │   └── ssh_client.py        # SSH 客户端
│   ├── feedback/
│   │   ├── __init__.py
│   │   ├── result_parser.py     # 执行结果解析
│   │   ├── error_analyzer.py    # 错误分析
│   │   └── self_heal.py         # 自愈逻辑
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── report_generator.py  # 报告生成
│   │   └── audit_log.py         # 审计日志
│   └── main_agent.py            # 主代理编排器
├── data/
│   ├── policies/
│   │   ├── cis/                 # CIS 基准文件
│   │   ├── nist/                # NIST 标准文件
│   │   └── stig/                # STIG 标准文件
│   ├── corpus/                  # 语料库
│   ├── knowledge_base/          # 知识库
│   └── test_results/            # 测试结果
├── ansible_playbooks/           # Ansible Playbooks 目录
├── configs/
│   ├── config.yaml              # 主配置文件
│   ├── api_keys.example.yaml    # API 密钥模板
│   └── model_selector.yaml      # 模型选择配置
├── docs/
│   ├── architecture.md          # 架构文档
│   ├── api_spec.md              # API 规范
│   └── runbook.md               # 运行手册
├── tests/
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── data/                    # 测试数据
├── requirements.txt             # 依赖
└── .env.example                 # 环境变量模板
```

---

## 🛠 核心模块功能说明

### 1. Preprocessing (`src/preprocessing/`)

| 文件 | 功能 | 关键方法 |
|------|------|----------|
| `pdf_parser.py` | 从 PDF 文档中提取文本 | `extract_text()`, `extract_sections()` |
| `text_cleaner.py` | 清洗和规范化文本 | `clean()`, `normalize()` |
| `chunker.py` | 将文本切分为适合向量化的块 | `chunk()`, `chunk_by_section()` |

### 2. Vector DB (`src/vector_db/`)

| 文件 | 功能 | 关键方法 |
|------|------|----------|
| `chroma_client.py` | ChromaDB 客户端 | `connect()`, `create_collection()`, `query()` |
| `embedding.py` | 文本嵌入生成 | `embed()`, `embed_batch()` |
| `persistence.py` | 数据持久化管理 | `save()`, `load()`, `backup()` |

### 3. RAG (`src/rag/`)

| 文件 | 功能 | 关键方法 |
|------|------|----------|
| `retriever.py` | 向量相似度检索 | `search()`, `retrieve()` |
| `ranker.py` | 结果重排序 | `rerank()`, `filter()` |
| `knowledge_store.py` | 统一知识存储接口 | `get()`, `put()`, `delete()` |

### 4. LLM (`src/llm/`)

| 文件 | 功能 | 关键方法 |
|------|------|----------|
| `llm_client.py` | LLM API 客户端 | `generate()`, `chat()` |
| `prompt_templates.py` | 提示词模板管理 | `get_template()`, `render()` |

### 5. Executor (`src/executor/`)

| 文件 | 功能 | 关键方法 |
|------|------|----------|
| `ansible_runner.py` | Ansible Playbook 执行 | `run()`, `run_async()` |
| `playbook_builder.py` | 动态构建 Playbook | `build_task()`, `build_play()` |
| `ssh_client.py` | SSH 连接与命令执行 | `connect()`, `exec()`, `upload()` |

### 6. Feedback (`src/feedback/`)

| 文件 | 功能 | 关键方法 |
|------|------|----------|
| `result_parser.py` | 解析执行结果 | `parse_stdout()`, `parse_stderr()` |
| `error_analyzer.py` | 分析错误原因 | `analyze()`, `categorize()` |
| `self_heal.py` | 自动修复逻辑 | `heal()`, `retry()` |

### 7. Reporting (`src/reporting/`)

| 文件 | 功能 | 关键方法 |
|------|------|----------|
| `report_generator.py` | 生成各类报告 | `generate_json()`, `generate_html()`, `generate_pdf()` |
| `audit_log.py` | 审计日志记录 | `log()`, `query()`, `export()` |

### 8. Main Agent (`src/main_agent.py`)

**SecurityHardeningAgent 类** - 主代理编排器

| 方法 | 功能 |
|------|------|
| `ingest_knowledge()` | 知识入库 |
| `search_knowledge()` | 知识检索 |
| `harden()` | 执行加固 |
| `generate_report()` | 生成报告 |

---

## 🔄 数据流 (Data Flow)

```
1. 知识入库流程
   PDF 文档 → Preprocessing → 向量数据库
   └─> 解析 → 清洗 → 分块 → 嵌入 → 存储

2. 查询处理流程
   用户查询 → RAG 检索 → 相关文档返回
   └─> 嵌入查询 → 相似度匹配 → 排序 → 过滤

3. 代码生成流程
   检索文档 → LLM → Ansible Playbook
   └─> 提示词构建 → LLM 推理 → YAML 验证

4. 执行流程
   Playbook → Executor → 执行结果
   └─> Ansible Runner → SSH → 命令执行 → 结果捕获

5. 反馈流程
   执行结果 → Feedback → 自愈/报告
   └─> 结果解析 → 错误分析 → (自愈重试) → 报告生成
```

---

## 📋 配置说明

### 配置文件位置

| 文件 | 用途 |
|------|------|
| `configs/config.yaml` | 主配置文件（路径、模型、执行参数等） |
| `configs/api_keys.example.yaml` | API 密钥模板（需复制为 `api_keys.yaml` 并填入真实密钥） |
| `configs/model_selector.yaml` | 模型选择规则（不同任务使用不同模型） |

### 环境变量

```bash
# .env 文件
OPENAI_API_KEY=your_api_key_here
CHROMA_DB_PATH=./vector_db/data
LOG_LEVEL=INFO
```

---

## 💻 使用示例

### 使用新架构

```python
from src.main_agent import SecurityHardeningAgent

# 初始化代理
agent = SecurityHardeningAgent(config_path="./configs/config.yaml")

# 知识入库
report = agent.ingest_knowledge("./data/policies/cis")

# 搜索知识
results = agent.search_knowledge("SSH configuration")

# 执行加固
result = agent.harden("SSH 配置", target_host="localhost")

# 生成报告
report_path = agent.generate_report("security_audit")
```

### 旧架构兼容（向后兼容）

```python
# 旧接口仍然可用
from src.agent import generate_ansible_code
from src.ingestion import SecurityBenchmarkIngester

# 这些接口仍然有效
```

---

## 🧪 测试规范

### 测试目录结构

```
tests/
├── unit/                    # 单元测试
│   ├── test_preprocessing.py
│   ├── test_vector_db.py
│   ├── test_rag.py
│   ├── test_llm.py
│   ├── test_executor.py
│   ├── test_feedback.py
│   └── test_reporting.py
├── integration/             # 集成测试
│   ├── test_ingestion_pipeline.py
│   ├── test_generation_pipeline.py
│   └── test_self_heal_loop.py
└── data/                    # 测试数据
    ├── sample_pdfs/
    ├── expected_outputs/
    └── fixtures/
```

### 运行测试

```bash
# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行所有测试并生成覆盖率报告
pytest --cov=src tests/
```

---

## 📊 性能指标 (Evaluation Metrics)

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

## 📝 开发原则

1. **模块化**: 每个模块职责单一，易于维护和测试
2. **可扩展性**: 新增功能应在独立模块中开发
3. **向后兼容**: 保留旧接口以确保平滑迁移
4. **分步确认**: 每个阶段完成后需运行验证测试

---

## 📚 相关文档

| 文档 | 路径 |
|------|------|
| 架构文档 | `docs/architecture.md` |
| API 规范 | `docs/api_spec.md` |
| 运行手册 | `docs/runbook.md` |
| 重构报告 | `REFACTOR_REPORT.md` |

---

**版本**: 2.0 (重构后)
**最后更新**: 2026-03-14
