# 项目进度记录表

## 1. 项目概况 (Project Overview)

**课题**: 基于大语言模型与 RAG 技术的智能化系统动态安全加固框架研究
**作者**: MOU LINGJIE
**版本**: 2.0 (重构后)
**最后更新**: 2026-03-14

---

## 2. 当前状态 (Current Status)

| 模块 | 状态 | 说明 |
|------|------|------|
| Preprocessing | ✅ 已完成 | 所有模块已实现，包含中文注释 |
| Vector DB | ✅ 已完成 | 所有模块已实现，包含中文注释 |
| RAG | ✅ 已完成 | 所有模块已实现，包含中文注释 |
| LLM | ✅ 已完成 | 所有模块已实现，包含中文注释 |
| Executor | ✅ 已完成 | `ansible_runner`/`playbook_builder`/`ssh_client` 已实现 |
| Feedback | ✅ 已完成 | 所有模块已实现，包含中文注释 |
| Reporting | ✅ 已完成 | 所有模块已实现，包含中文注释 |
| Main Agent | ✅ 已完成 | `main_agent.py` 已整合所有新模块 |

---

## 3. 开发里程碑 (Milestones)

### 阶段 1：知识入库 (Knowledge Ingestion) ✅ 已完成
- **目标**: 解析 PDF 安全基准文档并存入向量库
- **实现文件**:
  - 旧：`src/ingestion/processor.py`
  - 新：`src/preprocessing/*` + `src/vector_db/*`
- **完成情况**:
  - 处理 PDF 文件：3 个云安全基准文档 (1,868 个 chunks)
  - 向量数据库：持久化至 `./vector_db/` (23MB)
  - 验证搜索：测试通过

### 阶段 2：语义翻译引擎 (Semantic Reasoning) ✅ 已完成
- **目标**: 将检索到的文本翻译为合规的 Ansible Task
- **实现文件**:
  - 旧：`src/agent/generator.py`
  - 新：`src/llm/*`
- **完成情况**:
  - CodeGenerator 类已实现
  - System Prompt 设计完成
  - YAML 语法验证实现
  - 测试：5/5 通过

### 阶段 3：自动化执行模块 (Execution Engine) ✅ 已完成
- **目标**: 在目标系统上静默执行加固脚本并捕获全量日志
- **实现文件**: `src/executor/*`
- **完成情况**:
  - ✅ `ansible_runner.py` - Ansible Playbook 执行
  - ✅ `playbook_builder.py` - Playbook 构建器
  - ✅ `ssh_client.py` - SSH 客户端（非 Linux 环境使用 subprocess 模拟）
  - ✅ 返回结构化 JSON (status, stdout, stderr)

### 阶段 4：核心创新：闭环自愈逻辑 (Self-Healing Loop) ✅ 已完成
- **目标**: 实现系统检测到错误后的自动重写
- **实现文件**: `src/feedback/*`
- **完成情况**:
  - ✅ `result_parser.py` - 解析执行结果
  - ✅ `error_analyzer.py` - 分析错误原因
  - ✅ `self_heal.py` - 自动修复逻辑
  - ✅ 防御性设计：单个任务重试上限为 3 次

### 阶段 5：总控编排器 (Orchestrator) ✅ 已完成
- **目标**: 串联全流程，提供统一入口
- **实现文件**: `src/main_agent.py`
- **完成情况**:
  - ✅ 整合所有新模块到 `SecurityHardeningAgent` 类
  - ✅ 实现 `ingest_knowledge()` 方法
  - ✅ 实现 `search_knowledge()` 方法
  - ✅ 实现 `harden()` 方法
  - ✅ 实现 `generate_report()` 方法

### 阶段 6：实验验证与性能分析 (Evaluation) ✅ 已完成
- **目标**: 产生支撑论文假设的数据
- **实现文件**: `tests/benchmark.py`
- **完成情况**:
  - ✅ 单元测试：`tests/unit/test_preprocessing.py`
  - ✅ 单元测试：`tests/unit/test_vector_db.py`
  - ✅ 单元测试：`tests/unit/test_rag.py`
  - ✅ 单元测试：`tests/unit/test_llm.py`
  - ✅ 单元测试：`tests/unit/test_executor.py`
  - ✅ 单元测试：`tests/unit/test_feedback.py`
  - ✅ 单元测试：`tests/unit/test_reporting.py`
  - ✅ 集成测试：`tests/integration/test_main_agent.py`
  - ✅ `tests/benchmark.py` - 性能基准测试（已创建，5 项指标）

---

## 4. 完成的模块清单

### 4.1 Preprocessing 模块 ✅
- [x] `pdf_parser.py` - PDF 文档解析（PDFParser 类）
- [x] `text_cleaner.py` - 文本清洗与规范化（TextCleaner 类）
- [x] `chunker.py` - 文本分块（Chunker 类，TextChunk 数据类）
- [x] `__init__.py` - 模块导出

### 4.2 Vector DB 模块 ✅
- [x] `chroma_client.py` - ChromaDB 客户端（ChromaClient 类）
- [x] `embedding.py` - 嵌入模型管理（EmbeddingModel 类）
- [x] `persistence.py` - 数据持久化（VectorStorePersistence 类）
- [x] `__init__.py` - 模块导出

### 4.3 RAG 模块 ✅
- [x] `retriever.py` - 向量检索（Retriever 类，RetrievalResult 数据类）
- [x] `ranker.py` - 结果排序（Ranker 类，RankedResult 数据类）
- [x] `knowledge_store.py` - 统一知识存储接口（KnowledgeStore 类）
- [x] `__init__.py` - 模块导出

### 4.4 LLM 模块 ✅
- [x] `llm_client.py` - LLM API 客户端（LLMClient、LLMResponse 类）
- [x] `prompt_templates.py` - 提示词模板管理（PromptTemplate、SystemPrompt 类）
- [x] `__init__.py` - 模块导出

### 4.5 Executor 模块 ✅
- [x] `ansible_runner.py` - Ansible Playbook 执行（AnsibleRunner、ExecutionResult 类）
- [x] `playbook_builder.py` - Playbook 构建器（PlaybookBuilder、Task 数据类）
- [x] `ssh_client.py` - SSH 客户端（SSHClient、SSHConfig、SSHResult 类）
- [x] `__init__.py` - 模块导出

### 4.6 Feedback 模块 ✅
- [x] `result_parser.py` - 执行结果解析（ResultParser、ExecutionResult 类）
- [x] `error_analyzer.py` - 错误分析（ErrorAnalyzer、ErrorAnalysis 类）
- [x] `self_heal.py` - 自愈逻辑（SelfHealer、HealingResult 类）
- [x] `__init__.py` - 模块导出

### 4.7 Reporting 模块 ✅
- [x] `report_generator.py` - 报告生成（ReportGenerator、ReportEntry 类）
- [x] `audit_log.py` - 审计日志（AuditLog 类）
- [x] `__init__.py` - 模块导出

### 4.8 Main Agent ✅
- [x] `main_agent.py` - 主代理编排器（SecurityHardeningAgent 类）
  - [x] `ingest_knowledge()` - 知识入库
  - [x] `search_knowledge()` - 知识检索
  - [x] `generate_playbook()` - Playbook 生成
  - [x] `harden()` - 执行加固
  - [x] `generate_report()` - 报告生成
  - [x] `get_stats()` - 统计信息

---

## 5. 测试文件清单

### 单元测试 (tests/unit/)
- [x] `test_preprocessing.py` - Preprocessing 模块测试
- [x] `test_vector_db.py` - Vector DB 模块测试
- [x] `test_rag.py` - RAG 模块测试
- [x] `test_llm.py` - LLM 模块测试
- [x] `test_executor.py` - Executor 模块测试
- [x] `test_feedback.py` - Feedback 模块测试
- [x] `test_reporting.py` - Reporting 模块测试

### 集成测试 (tests/integration/)
- [x] `test_main_agent.py` - Main Agent 集成测试

### 测试工具
- [x] `tests/run_tests.py` - 测试运行脚本

---

## 6. 项目结构 (Project Structure)

> 最后校验日期：2026-03-18（与实际文件系统一致）

```
mastercode-linux/
├── src/                        # 核心源代码
│   ├── __init__.py
│   ├── main_agent.py           # 主代理编排器 ✅
│   ├── preprocessing/          # PDF 解析、文本清洗、分块 ✅
│   │   ├── __init__.py
│   │   ├── pdf_parser.py
│   │   ├── text_cleaner.py
│   │   └── chunker.py
│   ├── vector_db/              # 向量数据库管理 ✅
│   │   ├── __init__.py
│   │   ├── chroma_client.py
│   │   ├── embedding.py
│   │   └── persistence.py
│   ├── rag/                    # 检索增强生成 ✅
│   │   ├── __init__.py
│   │   ├── retriever.py
│   │   ├── ranker.py
│   │   └── knowledge_store.py
│   ├── llm/                    # LLM 客户端和提示词 ✅
│   │   ├── __init__.py
│   │   ├── llm_client.py
│   │   └── prompt_templates.py
│   ├── executor/               # 执行模块 ✅
│   │   ├── __init__.py
│   │   ├── ansible_runner.py
│   │   ├── playbook_builder.py
│   │   └── ssh_client.py
│   ├── feedback/               # 反馈和自愈 ✅
│   │   ├── __init__.py
│   │   ├── result_parser.py
│   │   ├── error_analyzer.py
│   │   └── self_heal.py
│   ├── reporting/              # 报告和审计 ✅
│   │   ├── __init__.py
│   │   ├── report_generator.py
│   │   └── audit_log.py
│   └── utils/                  # 工具函数 ✅
│       └── yaml_utils.py
├── tests/                      # 测试 ✅
│   ├── __init__.py
│   ├── conftest.py
│   ├── run_tests.py
│   ├── data/
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_preprocessing.py
│   │   ├── test_vector_db.py
│   │   ├── test_rag.py
│   │   ├── test_llm.py
│   │   ├── test_executor.py
│   │   ├── test_feedback.py
│   │   └── test_reporting.py
│   └── integration/
│       ├── __init__.py
│       └── test_main_agent.py
├── doc/                        # 安全基准文档（PDF/YAML/Profile）
│   ├── CIS_*.pdf               # 3 个 CIS 云安全基准 PDF
│   ├── *-CIS-baseline.yml      # RHEL9/Ubuntu22 CIS 基线
│   ├── *-CIS-controls.yml      # RHEL9/Ubuntu22 CIS 控制项
│   ├── *.profile               # RHEL9/Ubuntu22 安全 Profile
│   ├── *-product-info.yml      # 产品信息
│   ├── Linux-Security-Baseline.md
│   ├── Rocky9-Hardening-Guide.md
│   ├── Ubuntu-Hardening-Guide.adoc
│   └── README.md
├── docs/                       # 项目文档 ✅
│   ├── architecture.md
│   ├── api_spec.md
│   └── runbook.md
├── codeplan/                   # 项目规划
│   ├── Full_Project_Spec.md
│   └── project_structure_no_comments.md
├── configs/                    # 配置文件 ✅
│   ├── config.yaml
│   ├── api_keys.yaml
│   ├── api_keys.example.yaml
│   └── model_selector.yaml
├── data/                       # 数据目录
│   ├── policies/               # 策略文件 (cis/nist/stig)
│   ├── corpus/                 # 语料库
│   ├── knowledge_base/         # 知识库
│   ├── raw/                    # 原始数据
│   └── test_results/           # 测试结果
├── examples/                   # 使用示例
│   └── basic_usage.py
├── reports/                    # 生成的报告
├── audit_logs/                 # 审计日志
├── ansible_playbooks/          # Ansible Playbooks
├── dev_log/                    # 开发日志
├── vector_db/                  # 向量数据库持久化 (ChromaDB)
│   └── chroma.sqlite3
├── theme/                      # 课题相关文件
├── test_audit/                 # 测试审计输出
├── test_db/                    # 测试数据库输出
├── test_reports/               # 测试报告输出
├── venv/                       # Python 虚拟环境
├── requirements.txt            # 依赖 ✅
├── package.py                  # 打包脚本
├── pyrightconfig.json          # Pyright 配置
├── plan.md                     # 项目进度记录（本文件）
├── fix.md                      # 修复记录
├── suggestion.md               # 修改建议
├── README.md                   # 项目说明
├── .env                        # 环境变量（不入库）
├── .env.example                # 环境变量模板 ✅
└── .gitignore
```

---

## 7. 遗留问题与阻塞点 (Blockers / Known Issues)

### 当前限制
1. **Windows 环境限制**: Ansible 控制节点需要 Linux
   - **解决方案**: 在 WSL 或 Docker 中测试真实 Ansible 执行
   - **当前状态**: `ssh_client.py` 和 `ansible_runner.py` 使用 subprocess 模拟

2. **规则提取精度**: 部分章节编号和标题提取不准确
   - **影响**: 不影响功能，但降低可读性
   - **解决方案**: 优化正则表达式

3. **LLM API 依赖**: 需要 OpenAI API Key
   - **当前状态**: 已实现模拟模式，无 API Key 时返回模拟响应
   - **解决方案**: 设置 `.env` 文件配置 `OPENAI_API_KEY`

### 技术债务
- [ ] 需要清理旧的向量数据目录

---

## 12. 旧模块删除记录

**删除日期**: 2026-03-14

已删除的旧模块：
- `src/ingestion/` - 已被 `preprocessing/` + `vector_db/` + `rag/` 替代
- `src/agent/` - 已被 `llm/` + `rag/` + `feedback/` 替代

`src/__init__.py` 已更新，移除了向后兼容性导入。

新架构导入：
```python
from src import SecurityHardeningAgent  # 主代理
from src.preprocessing import PDFParser, TextCleaner, Chunker
from src.vector_db import ChromaClient, EmbeddingModel
from src.rag import Retriever, Ranker, KnowledgeStore
from src.llm import LLMClient, PromptTemplate
from src.executor import AnsibleRunner, PlaybookBuilder, SSHClient
from src.feedback import ResultParser, ErrorAnalyzer, SelfHealer
from src.reporting import ReportGenerator, AuditLog
```

---

## 8. 开发约束 (Constraints)

1. **模块化原则**: 不要改动已完成并通过测试的模块
2. **安全性**: 不要将 API Key 硬编码，必须读取 `.env` 文件
3. **分步确认**: 完成每个阶段后必须运行验证测试
4. **错误处理**: 遇到无法解决的错误先跳过，在 `dev_log/` 中记录
5. **中文注释**: 所有函数和类必须包含中文注释

---

## 9. 快速启动命令

```bash
# 运行单元测试
python tests/run_tests.py

# 或使用 pytest
pytest tests/unit/ -v
pytest tests/integration/ -v

# 运行覆盖率测试
pytest --cov=src tests/

# 运行 Main Agent
python -c "from src.main_agent import SecurityHardeningAgent; agent = SecurityHardeningAgent(); print(agent.get_stats())"
```

---

## 10. 相关文档

| 文档 | 路径 |
|------|------|
| 项目规范 | `Full_Project_Spec.md` |
| 架构文档 | `docs/architecture.md` |
| API 规范 | `docs/api_spec.md` |
| 运行手册 | `docs/runbook.md` |
| 重构报告 | `REFACTOR_REPORT.md` |
| 项目进度 | `plan.md` |

---

## 11. 本次完成内容总结

### 已完成的核心功能
1. ✅ **Preprocessing 模块**: PDF 解析、文本清洗、文本分块
2. ✅ **Vector DB 模块**: ChromaDB 客户端、嵌入模型、持久化管理
3. ✅ **RAG 模块**: 向量检索、结果排序、知识存储
4. ✅ **LLM 模块**: LLM 客户端、提示词模板
5. ✅ **Executor 模块**: Ansible 执行器、Playbook 构建器、SSH 客户端
6. ✅ **Feedback 模块**: 结果解析、错误分析、自愈逻辑
7. ✅ **Reporting 模块**: 报告生成、审计日志
8. ✅ **Main Agent**: 总控编排器，整合所有模块

### 已完成的测试
- ✅ 7 个单元测试文件（覆盖所有模块）
- ✅ 1 个集成测试文件（Main Agent）
- ✅ 测试运行脚本

### 代码特点
- 所有函数和类都包含详细的中文注释
- 使用数据类（dataclass）进行数据封装
- 支持模拟模式（无 API Key 时可测试）
- 完整的错误处理和日志记录

---

## 13. 2026-03-17 工作记录

### 时间
2026 年 3 月 17 日

### 本次工作范围与成果

#### 1. Linux 兼容性检测
- 全面扫描 `src/`、`tests/`、`examples/` 中所有 `.py` 文件，检查路径处理、编码、行尾符、进程调用等跨平台问题
- **结论**：源代码（`src/`）Linux 兼容性良好 — 全面使用 `pathlib.Path`、`./` 相对路径、`encoding="utf-8"`，无硬编码 Windows 路径
- 发现 `package.py` L148 中 `shell=True` + f-string 路径拼接安全风险（仅 Linux 执行路径）

#### 2. 架构图 vs 代码差距分析
对照 `codeplan/Full_Project_Spec.md` 中的架构图与实际代码，识别出 9 项差距：
- **知识回写闭环缺失**：架构图标注"成功模式向量化存储"，但 `harden()` 成功后不回写 Vector DB
- **Ranker 未集成**：`ranker.py` 实现完好但从未在检索管线中使用
- **KnowledgeStore / ChromaClient 缺少 CRUD**：缺 `get()`、`put()`、`delete()` 方法
- **model_selector.yaml 未被引用**：`LLMClient` 硬编码 `deepseek-chat`
- **VectorStorePersistence 未集成**：`persistence.py` 孤立未被任何模块使用
- **HardeningPlan/HardeningStep 定义缺失**：导入不存在的 `agent.hardening_agent` 模块
- 多项小修复（`EmbeddingModel.dimension` 无缓存、`ChromaClient.clear()` 可能报错等）

#### 3. 导入风格审计
- 扫描 `src/` 内所有 40+ 处内部导入语句
- 发现 `src/vector_db/__init__.py`（3 处）和 `src/main_agent.py` 懒加载（3 处）使用绝对导入，与其余相对导入不一致

#### 4. 遗留兼容代码扫描
- `src/executor/ansible_runner.py`：`from agent.hardening_agent import ...` 导致 4 个函数成为死代码
- `src/feedback/self_heal.py`：向后兼容路径（无 `execute_fn` 回调时仅靠关键词判断）
- `tests/test_stage2.py`：引用完全不存在的 `agent.generator` / `agent.rag_querier` 旧模块

#### 5. 输出文件
- 生成 `suggestion.md`：包含全部 9 项修改建议、代码示例、优先级排序及可直接发送给 Claude Code 的完整提示词

### 遗留问题

| # | 问题 | 严重程度 | 状态 |
|---|------|----------|------|
| 1 | 13 个文件存在未解决的 Git 合并冲突 | 🔴 严重 | 待修复 |
| 2 | 知识回写闭环未实现（架构核心特性） | 🔴 高 | 待实现 |
| 3 | Ranker 未集成进检索管线 | 🟠 高 | 待实现 |
| 4 | KnowledgeStore / ChromaClient 缺 CRUD | 🟠 中 | 待实现 |
| 5 | model_selector.yaml 未被 LLMClient 加载 | 🟡 中 | 待实现 |
| 6 | VectorStorePersistence 孤立未集成 | 🟡 中 | 待实现 |
| 7 | HardeningPlan/HardeningStep 模块不存在 | 🟡 低 | 待定义 |
| 8 | `src/vector_db/__init__.py` 导入风格不一致 | 🟡 低 | 待统一 |
| 9 | `tests/test_stage2.py` 引用旧架构模块 | 🟠 中 | 待重写或删除 |
| 10 | `package.py` shell=True 安全风险 | 🟡 低 | 待修复 |
| 11 | 性能基准测试 `tests/benchmark.py` 未创建 | 🟡 低 | 待创建 |

> 详细修改建议及 Claude Code 提示词见 `suggestion.md`

---

## 14. 2026-03-18 工作记录

### 时间
2026 年 3 月 18 日

### 本次工作范围与成果

#### 1. 项目运行状态检查
- 激活虚拟环境（`source venv/bin/activate`）后执行 `import src` 验证项目可用性
- 发现 2 个导入级别错误，导致项目无法启动

#### 2. Bug 修复

##### 2.1 `src/main_agent.py` 缺少 `import re`（🔴 阻断性）
- **现象**：`import src` 时抛出 `NameError: name 're' is not defined`
- **原因**：`SecurityHardeningAgent` 类属性 `_CIS_RULE_RE = re.compile(...)` 使用了 `re` 模块，但文件头部未导入
- **修复**：在文件头部添加 `import re`

##### 2.2 `src/main_agent.py` 存在未使用的导入 `looks_like_yaml`（🟡 代码质量）
- **现象**：`from .utils.yaml_utils import extract_yaml, looks_like_yaml` 中 `looks_like_yaml` 导入后从未被直接使用
- **原因**：`looks_like_yaml` 是 `extract_yaml()` 的内部依赖，`main_agent.py` 仅通过 `extract_yaml()` 间接调用
- **修复**：移除多余导入，改为 `from .utils.yaml_utils import extract_yaml`

#### 3. 测试验证
- 修复后运行全量测试：`python -m pytest tests/ -v`
- 结果：**101 个测试全部通过**（9.94s）
- 项目导入验证：`import src` → `src package OK` ✅

#### 4. Issue #5 修复：接线 model_selector.yaml
- **问题**：`LLMClient` 有 `model_config_path` 参数但 `main_agent.py` 未传入；`_select_model_for_task()` 读取 `tasks` 键但 YAML 实际使用 `models` 键
- **修复内容**：
  - `src/main_agent.py`：`_init_components()` 中传入 `model_config_path="./configs/model_selector.yaml"`
  - `src/llm/llm_client.py`：`_select_model_for_task()` 改为读取 `models` 键，并同步应用 `temperature`
  - `src/main_agent.py`：`generate_playbook()` 传入 `task_type="code_generation"`
  - `src/feedback/self_heal.py`：`_rewrite_playbook()` 传入 `task_type="error_analysis"`

#### 5. Issue #11 实现：创建 tests/benchmark.py
- 创建 `tests/benchmark.py`，覆盖 Full_Project_Spec.md 中的 5 项性能指标：
  - 知识检索准确率（目标 > 90%）
  - 代码生成准确率（目标 > 85%）
  - 自愈成功率（目标 > 70%）
  - 平均响应时间（目标 < 30s）
  - 加固覆盖率（目标 > 80%）
- 支持 Mock 和 Live 两种模式：`python tests/benchmark.py` / `python tests/benchmark.py --live`
- 报告自动保存至 `data/test_results/benchmark_*.json`

#### 6. Live 模式调试：.env 加载与 API Key 链路修复

##### 6.1 `src/llm/llm_client.py` 未加载 `.env` 文件（🔴 阻断性）
- **现象**：`--live` 模式下 API Key 为 `None`，LLM 请求全部失败
- **原因**：`os.getenv("DEEPSEEK_API_KEY")` 无法读到值，因为模块未调用 `load_dotenv()`
- **修复**：
  1. 在 `llm_client.py` 顶部增加 `from dotenv import load_dotenv; load_dotenv()`
  2. 新增 API Key 回退链：`api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")`
  3. 新增 Base URL 回退：`base_url or os.getenv("OPENAI_BASE_URL") or self.DEFAULT_BASE_URL`

##### 6.2 `tests/unit/test_llm.py` 测试回归（🟠 中）
- **现象**：`load_dotenv()` 导致 `.env` 中的真实 API Key 注入环境变量，3 个原本依赖 Mock 模式的测试开始调用真实 API 失败
- **修复**：对 `test_init_without_api_key`、`test_generate_mock`、`test_generate_batch` 三个测试添加 `@patch.dict(os.environ, {}, clear=True)` 装饰器，隔离环境变量

#### 7. Benchmark 验证标准调整
- **问题**：代码生成验证要求输出包含 `hosts:`、`tasks:`、`- name:`（完整 Playbook 结构），但 Prompt Template 设计为输出 task 级 YAML（仅含 `- name:` 任务列表）
- **修复**：将 `required_elements` 从 `["hosts:", "tasks:", "- name:"]` 简化为 `["- name:"]`，与 Prompt Template 一致

#### 8. Live 模式基准测试结果

**测试环境**：DeepSeek API (`deepseek-chat`)，向量库 `./vector_db/`（CIS 安全基准文档）

| 指标 | 目标 | Mock 结果 | Live 结果 | 状态 |
|------|------|-----------|-----------|------|
| 知识检索准确率 | > 90% | 40.0% ❌ | 70.0% ❌ | 受文档覆盖面限制 |
| 代码生成准确率 | > 85% | 100.0% ✅ | 100.0% ✅ | ✅ |
| 自愈成功率 | > 70% | 66.7% ❌ | 66.7% ❌ | 差 3.3%，受 Mock 执行回调限制 |
| 平均响应时间 | < 30s | 0.04s ✅ | 3.68s ✅ | ✅ |
| 加固覆盖率 | > 80% | 100.0% ✅ | 80.0% ✅ | ✅ |

- **总耗时**：287.5 秒
- **通过率**：3/5（60%）
- **报告路径**：`data/test_results/benchmark_20260318_040843.json`

**未达标指标分析**：
- **知识检索准确率 70%**：向量库中的 CIS 文档未充分覆盖 firewall、file permissions、kernel parameters、cron jobs 等查询关键词，需补充更多安全基准文档
- **自愈成功率 66.7%**：仅差 3.3%，受限于 benchmark 中 Mock 执行回调的设计（第二次执行固定成功），真实环境需更精细的 LLM 重写提示词

### 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `src/main_agent.py` | 添加 `import re`；移除 `looks_like_yaml`；传入 `model_config_path`；`generate_playbook` 传 `task_type` |
| `src/llm/llm_client.py` | 添加 `load_dotenv()`；API Key/Base URL 回退链；`_select_model_for_task()` 读取 `models` 键并应用 `temperature` |
| `src/feedback/self_heal.py` | `_rewrite_playbook()` 传入 `task_type="error_analysis"` |
| `tests/unit/test_llm.py` | 添加 `import os`；3 个测试添加 `@patch.dict(os.environ, {}, clear=True)` 隔离环境变量 |
| `tests/benchmark.py` | 新建：5 项性能基准测试；调整验证标准匹配 Prompt Template 输出格式 |

### 遗留问题更新

| # | 问题 | 严重程度 | 状态 |
|---|------|----------|------|
| 1 | ~~13 个文件存在未解决的 Git 合并冲突~~ | ~~🔴 严重~~ | ✅ 已修复 |
| 2 | ~~知识回写闭环未实现（架构核心特性）~~ | ~~🔴 高~~ | ✅ 已实现（`harden()` 成功后回写 Vector DB） |
| 3 | ~~Ranker 未集成进检索管线~~ | ~~🟠 高~~ | ✅ 已集成（`KnowledgeStore.search()` 调用 `Ranker.rank()`） |
| 4 | ~~KnowledgeStore / ChromaClient 缺 CRUD~~ | ~~🟠 中~~ | ✅ 已实现（`get()`/`put()`/`delete()` 方法） |
| 5 | ~~model_selector.yaml 未被 LLMClient 加载~~ | ~~🟡 中~~ | ✅ 已修复（main_agent 传入配置路径，_select_model_for_task 读取 models 键） |
| 6 | ~~VectorStorePersistence 孤立未集成~~ | ~~🟡 中~~ | ✅ 已集成（`KnowledgeStore` 中使用） |
| 7 | ~~HardeningPlan/HardeningStep 模块不存在~~ | ~~🟡 低~~ | ✅ 已定义（`ansible_runner.py` 中 dataclass） |
| 8 | ~~`src/vector_db/__init__.py` 导入风格不一致~~ | ~~🟡 低~~ | ✅ 已统一（全部使用相对导入） |
| 9 | ~~`tests/test_stage2.py` 引用旧架构模块~~ | ~~🟠 中~~ | ✅ 已删除 |
| 10 | ~~`package.py` shell=True 安全风险~~ | ~~🟡 低~~ | ✅ 已修复（改用列表参数 subprocess 调用） |
| 11 | ~~性能基准测试 `tests/benchmark.py` 未创建~~ | ~~🟡 低~~ | ✅ 已创建并完成 Live 测试（3/5 通过） |
| 12 | ~~`main_agent.py` 缺少 `import re`~~ | ~~🔴 阻断~~ | ✅ 已修复 |
| 13 | ~~`main_agent.py` 未使用的 `looks_like_yaml` 导入~~ | ~~🟡 低~~ | ✅ 已修复 |
| 14 | ~~`llm_client.py` 未加载 `.env`~~ | ~~🔴 阻断~~ | ✅ 已修复（`load_dotenv()` + 回退链） |
| 15 | ~~`test_llm.py` 因 dotenv 导致测试回归~~ | ~~🟠 中~~ | ✅ 已修复（`patch.dict` 隔离） |

### 待优化项（非阻断）

| # | 项目 | 说明 |
|---|------|------|
| A | 知识检索准确率提升 | 当前 70%，目标 90%。需补充 firewall/kernel/cron 等安全基准文档至向量库 |
| B | 自愈成功率提升 | 当前 66.7%，目标 70%。需优化 LLM 重写提示词或调整 benchmark 测试用例 |

---

**最后更新**: 2026-03-18
**架构版本**: 2.0 (重构后)
**当前状态**: 全部 15 项遗留问题已解决；101 个单元/集成测试通过；Live 基准测试 3/5 通过；阶段 1-6 全部完成
