# 项目重构报告

## 重构日期：2026-03-14

## 重构目标

根据 `project_structure_no_comments.md` 文件中定义的目标结构，对项目进行全面重构。

## 重构前后对比

### 原始结构
```
src/
├── ingestion/         # 知识入库模块
├── agent/             # LLM 推理 + 代码生成
└── executor/          # Ansible 执行
```

### 新结构
```
src/
├── preprocessing/     # PDF 解析、文本清洗、分块
│   ├── __init__.py
│   ├── pdf_parser.py
│   ├── text_cleaner.py
│   └── chunker.py
├── vector_db/         # 向量数据库管理
│   ├── __init__.py
│   ├── chroma_client.py
│   ├── embedding.py
│   └── persistence.py
├── rag/               # 检索增强生成
│   ├── __init__.py
│   ├── retriever.py
│   ├── ranker.py
│   └── knowledge_store.py
├── llm/               # LLM 客户端和提示词
│   ├── __init__.py
│   ├── llm_client.py
│   └── prompt_templates.py
├── executor/          # 执行模块 (更新)
│   ├── __init__.py
│   ├── ansible_runner.py
│   ├── playbook_builder.py (新增)
│   └── ssh_client.py (新增)
├── feedback/          # 反馈和自愈 (新增)
│   ├── __init__.py
│   ├── result_parser.py
│   ├── error_analyzer.py
│   └── self_heal.py
├── reporting/         # 报告和审计 (新增)
│   ├── __init__.py
│   ├── report_generator.py
│   └── audit_log.py
└── main_agent.py      # 主代理 (新增)
```

## 新增目录

| 目录 | 说明 |
|-----|------|
| `data/policies/cis/` | CIS 策略文件 |
| `data/policies/nist/` | NIST 策略文件 |
| `data/policies/stig/` | STIG 策略文件 |
| `data/corpus/` | 语料库 |
| `data/knowledge_base/` | 知识库 |
| `data/test_results/` | 测试结果 |
| `ansible_playbooks/` | Ansible Playbooks |
| `configs/` | 配置文件 |
| `docs/` | 文档 |
| `tests/unit/` | 单元测试 |
| `tests/integration/` | 集成测试 |
| `tests/data/` | 测试数据 |

## 新增文件

### 配置文件 (`configs/`)
- `config.yaml` - 主配置文件
- `api_keys.example.yaml` - API 密钥模板
- `model_selector.yaml` - 模型选择配置

### 文档文件 (`docs/`)
- `architecture.md` - 架构文档
- `api_spec.md` - API 规范
- `runbook.md` - 运行手册

### 测试文件 (`tests/`)
- `tests/unit/__init__.py`
- `tests/integration/__init__.py`
- `tests/data/__init__.py`

## 模块功能映射

| 原始模块 | 新模块 | 功能说明 |
|---------|-------|---------|
| `ingestion/knowledge_ingestion.py` | `preprocessing/*` + `vector_db/*` | PDF 处理和向量存储 |
| `agent/rag_querier.py` | `rag/retriever.py` | RAG 检索 |
| `agent/hardening_agent.py` | `rag/ranker.py` | 结果排序 |
| `agent/generator.py` | `llm/*` | LLM 代码生成 |
| - | `feedback/*` | 错误分析和自愈 |
| - | `reporting/*` | 报告生成和审计 |
| - | `main_agent.py` | 主代理编排 |

## 向后兼容性

为保持向后兼容，保留了以下旧模块：
- `src/ingestion/` - 继续可用
- `src/agent/` - 继续可用
- `src/executor/ansible_runner.py` - 更新但保留

所有旧接口仍可通过 `src/__init__.py` 导入。

## 使用新结构的示例

```python
# 使用新架构
from src.main_agent import SecurityHardeningAgent

agent = SecurityHardeningAgent()

# 知识入库
report = agent.ingest_knowledge("./doc")

# 搜索知识
results = agent.search_knowledge("SSH configuration")

# 执行加固
result = agent.harden("SSH 配置", target_host="localhost")

# 生成报告
report_path = agent.generate_report("security_audit")
```

## 使用旧结构的示例 (仍然有效)

```python
# 使用旧架构 (向后兼容)
from src.agent import generate_ansible_code
from src.ingestion import SecurityBenchmarkIngester

# 这些接口仍然有效
```

## 重构优势

1. **模块化**: 每个模块职责单一，易于维护和测试
2. **可扩展性**: 新增功能可以在独立模块中开发
3. **清晰的依赖关系**: 模块间依赖关系明确
4. **完整的反馈循环**: 新增 feedback 和 reporting 模块
5. **自愈能力**: 新增 self_heal 模块实现自动修复
6. **审计追踪**: 新增 audit_log 记录所有操作

## 下一步

1. 将旧代码逐步迁移到新模块
2. 添加单元测试
3. 更新文档
4. 集成测试
