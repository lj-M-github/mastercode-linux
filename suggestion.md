# 架构图 vs 实际代码：差距分析与修改建议

**生成日期**: 2026-03-17  
**基于**: `codeplan/Full_Project_Spec.md` 架构图与源代码对比

---

## 目录

- [前置任务：解决 Git 合并冲突](#前置任务解决-git-合并冲突)
- [修改 1：实现知识回写闭环](#修改-1实现知识回写闭环)
- [修改 2：集成 Ranker 到检索管线](#修改-2集成-ranker-到检索管线)
- [修改 3：补全 CRUD 操作](#修改-3补全-crud-操作)
- [修改 4：加载 model_selector.yaml](#修改-4加载-model_selectoryaml)
- [修改 5：集成 VectorStorePersistence](#修改-5集成-vectorstorepersistence)
- [修改 6：修复 HardeningPlan/HardeningStep 依赖](#修改-6修复-hardeningplanhardeningstep-依赖)
- [修改 7：小修复](#修改-7小修复)
- [修改 8：统一导入风格](#修改-8统一导入风格)
- [修改 9：清理遗留兼容代码](#修改-9清理遗留兼容代码)
- [附录：给 Claude Code 的完整提示词](#附录给-claude-code-的完整提示词)

---

## 前置任务：解决 Git 合并冲突

**严重程度**: 🔴 严重（任何平台都无法运行）

以下 13 个文件第 1 行均为 `<<<<<<< HEAD`，包含未解决的 Git 合并冲突，Python 会直接报 SyntaxError。

| 文件 | 冲突范围 |
|------|----------|
| `examples/basic_usage.py` | L1-L415（整个文件） |
| `tests/run_tests.py` | L1-L113 |
| `tests/test_stage2.py` | L1-L565 |
| `tests/data/__init__.py` | L1-L5 |
| `tests/integration/__init__.py` | L1-L5 |
| `tests/integration/test_main_agent.py` | L1-L367 |
| `tests/unit/__init__.py` | L1-L5 |
| `tests/unit/test_executor.py` | L1-L381 |
| `tests/unit/test_feedback.py` | L1-L505 |
| `tests/unit/test_llm.py` | L1-L219 |
| `tests/unit/test_preprocessing.py` | L1-L221 |
| `tests/unit/test_rag.py` | L1-L205 |
| `tests/unit/test_reporting.py` | L1-L389 |

---

## 修改 1：实现知识回写闭环

**严重程度**: 🔴 高优先  
**涉及文件**: `src/main_agent.py`  
**架构图关键词**: "成功模式向量化存储 (Knowledge Update)"

### 问题描述

架构图中反馈层到向量知识库有一条明确的反馈箭头，标注为"成功模式向量化存储 (Knowledge Update)"。这意味着**成功执行的 playbook 应回写到向量数据库**，形成"经验学习"闭环，让后续类似任务可以复用已验证的成功方案。

### 当前代码

`main_agent.py` 的 `harden()` 方法（L382-L497）在执行成功后：
- ✅ 调用 `report_generator.add_result()` — 写入报告
- ✅ 调用 `audit_log.log_execution()` — 写入审计日志
- ❌ **从未调用 `knowledge_store.add()`** — 不回写向量库

### 所需修改

在 `harden()` 方法中，当某条规则的 playbook 执行成功后，将成功的 playbook 内容和规则元数据回写到 `self.knowledge_store.add()`，例如：

```python
# 在执行成功的分支中添加：
if execution_result.success:
    self.knowledge_store.add([{
        "content": playbook_content,
        "metadata": {
            "rule_id": rule_id,
            "type": "verified_playbook",
            "source": "self_execution",
            "target_host": target_host,
            "timestamp": datetime.now().isoformat()
        }
    }])
```

---

## 修改 2：集成 Ranker 到检索管线

**严重程度**: 🟠 高优先  
**涉及文件**: `src/rag/knowledge_store.py`, `src/rag/ranker.py`  
**架构图关键词**: RAG 模块中的"结果排序"

### 问题描述

`src/rag/ranker.py` 有完整实现（`rank()`、`filter_by_metadata()`、`boost_by_relevance()`），但 **`KnowledgeStore` 和 `Retriever` 完全不引用它**。架构图中 RAG 模块应包含"检索 + 排序"两个步骤。

### 当前代码

`knowledge_store.py` 的 `search()` 方法直接返回 `self.retriever.search()` 的结果，未经任何排序优化。

### 所需修改

在 `KnowledgeStore.__init__()` 中初始化 `Ranker`，在 `search()` 中先检索再排序：

```python
from rag.ranker import Ranker

class KnowledgeStore:
    def __init__(self, ...):
        # ... 已有初始化 ...
        self.ranker = Ranker()

    def search(self, query, n_results=5, filter_dict=None):
        # 1. 初始检索（多取一些候选）
        raw_results = self.retriever.search(query, n_results=n_results * 2, filter_dict=filter_dict)
        # 2. 重排序
        ranked = self.ranker.rank(raw_results, query=query, top_k=n_results)
        return ranked
```

---

## 修改 3：补全 CRUD 操作

**严重程度**: 🟠 中优先  
**涉及文件**: `src/vector_db/chroma_client.py`, `src/rag/knowledge_store.py`  
**规范要求**: `get()`, `put()`, `delete()` 方法

### 问题描述

规范明确要求 KnowledgeStore 提供 `get()`、`put()`、`delete()` 三个 CRUD 方法。当前只有 `add()` 和 `search()`。底层 `ChromaClient` 也只有 `add()` 和 `query()`，缺少按 ID 查询、更新、删除的能力。

### 所需修改

**ChromaClient 增加方法**：

```python
# src/vector_db/chroma_client.py

def get(self, ids: List[str]) -> Dict:
    """按 ID 查询文档。"""
    return self.collection.get(ids=ids)

def update(self, ids: List[str], embeddings=None, documents=None, metadatas=None) -> None:
    """更新已有文档。"""
    kwargs = {"ids": ids}
    if embeddings: kwargs["embeddings"] = embeddings
    if documents: kwargs["documents"] = documents
    if metadatas: kwargs["metadatas"] = metadatas
    self.collection.update(**kwargs)

def delete(self, ids: List[str]) -> None:
    """按 ID 删除文档。"""
    self.collection.delete(ids=ids)
```

**KnowledgeStore 增加方法**：

```python
# src/rag/knowledge_store.py

def get(self, item_id: str) -> Optional[Dict]:
    """按 ID 获取知识项。"""
    result = self.chroma_client.get(ids=[item_id])
    if result and result.get("documents"):
        return {"id": item_id, "content": result["documents"][0], "metadata": result["metadatas"][0]}
    return None

def put(self, item_id: str, content: str, metadata: Optional[Dict] = None) -> None:
    """更新或插入知识项。"""
    embedding = self.embedding_model.encode_single(content)
    self.chroma_client.update(ids=[item_id], embeddings=[embedding], documents=[content], metadatas=[metadata or {}])

def delete(self, item_id: str) -> None:
    """删除知识项。"""
    self.chroma_client.delete(ids=[item_id])
```

---

## 修改 4：加载 model_selector.yaml

**严重程度**: 🟡 中优先  
**涉及文件**: `src/llm/llm_client.py`, `configs/model_selector.yaml`

### 问题描述

`configs/model_selector.yaml` 定义了不同任务使用不同模型的规则，但 `LLMClient` 硬编码了 `deepseek-chat`，**完全不加载该配置文件**。架构图中 LLM 推理引擎应根据任务类型动态选择模型。

### 所需修改

`LLMClient` 应支持加载 `model_selector.yaml`，`generate()` 方法增加 `task_type` 参数：

```python
# src/llm/llm_client.py

def __init__(self, model="deepseek-chat", api_key=None, base_url=None, temperature=0.1, 
             model_config_path="./configs/model_selector.yaml"):
    self.model_config = self._load_model_config(model_config_path)
    # ...

def _load_model_config(self, path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

def generate(self, prompt, system_prompt=None, max_tokens=None, temperature=None, task_type=None):
    model = self.model
    if task_type and self.model_config:
        model = self.model_config.get("tasks", {}).get(task_type, {}).get("model", self.model)
    # 使用选定的 model 调用 API...
```

---

## 修改 5：集成 VectorStorePersistence

**严重程度**: 🟡 中优先  
**涉及文件**: `src/rag/knowledge_store.py`, `src/vector_db/persistence.py`

### 问题描述

`persistence.py` 实现了 `save_state()`、`load_state()`、`backup()` 方法，但**从未被任何模块引用**。知识库应在关键操作后保存状态。

### 所需修改

在 `KnowledgeStore` 中集成 `VectorStorePersistence`：

```python
# src/rag/knowledge_store.py

from vector_db.persistence import VectorStorePersistence

class KnowledgeStore:
    def __init__(self, db_path="./vector_db", ...):
        # ... 已有初始化 ...
        self.persistence = VectorStorePersistence(db_path)

    def add(self, items, show_progress=False):
        count = ...  # 原有添加逻辑
        self.persistence.save_state({"last_add_count": count, "total": self.get_stats().get("count", 0)})
        return count

    def delete(self, item_id):
        self.chroma_client.delete(ids=[item_id])
        self.persistence.save_state({"last_delete": item_id})
```

---

## 修改 6：修复 HardeningPlan/HardeningStep 依赖

**严重程度**: 🟡 低优先  
**涉及文件**: `src/executor/ansible_runner.py`

### 问题描述

`ansible_runner.py` L17-L20 尝试导入不存在的 `agent.hardening_agent.HardeningPlan` 和 `HardeningStep`，通过 `ImportError` fallback 为 `None`。依赖这些类型的 `run_step()`、`run_hardening()`、`execute_hardening_plan()` 方法无法正常使用。

### 所需修改

在 `ansible_runner.py` 内部定义 `HardeningPlan` 和 `HardeningStep` 数据类：

```python
# src/executor/ansible_runner.py（替换 L17-L20 的 try/except 导入块）

@dataclass
class HardeningStep:
    """单个加固步骤。"""
    name: str
    module: str
    params: Dict[str, Any] = field(default_factory=dict)
    when: str = ""

@dataclass
class HardeningPlan:
    """加固计划，包含多个步骤。"""
    plan_id: str
    rule_id: str
    description: str
    steps: List[HardeningStep] = field(default_factory=list)
    target_host: str = "localhost"
```

---

## 修改 7：小修复

### 7a. EmbeddingModel.dimension 缓存

**文件**: `src/vector_db/embedding.py` L65-68

当前每次调用 `dimension` property 都编码 "test" 字符串来获取维度，应缓存：

```python
def __init__(self, model_name="all-MiniLM-L6-v2"):
    self.model = SentenceTransformer(model_name)
    self._dimension = None  # 新增缓存

@property
def dimension(self):
    if self._dimension is None:
        self._dimension = len(self.encode_single("test"))
    return self._dimension
```

### 7b. ChromaClient.clear() 修复

**文件**: `src/vector_db/chroma_client.py` L130-133

`delete(where={})` 在 ChromaDB 中可能报错，改为删除集合后重建：

```python
def clear(self):
    """清空集合。"""
    self.client.delete_collection(self.collection_name)
    self.collection = self.client.get_or_create_collection(name=self.collection_name)
```

### 7c. SSHConfig.password 未使用

**文件**: `src/executor/ssh_client.py`

`SSHConfig.password` 字段存在但 `connect()`/`execute()` 中从未使用，仅支持密钥认证。如需密码认证可通过 `sshpass` 实现，或添加注释说明仅支持密钥。

### 7d. ReportGenerator 缺少 HTML/PDF 输出

**文件**: `src/reporting/report_generator.py`

规范中提到 `generate_html()` 和 `generate_pdf()`，但 `generate()` 方法仅支持 `json`/`markdown`/`text` 三种格式。可考虑添加 HTML 输出支持。

### 7e. package.py 中 shell=True 安全风险

**文件**: `package.py` L148

```python
# 当前（有安全风险）：
cmd = f"tar -czf {tar_path} -C {ROOT_DIR} -T {list_path}"
subprocess.run(cmd, shell=True, check=True)

# 修改为列表形式：
subprocess.run(["tar", "-czf", str(tar_path), "-C", str(ROOT_DIR), "-T", str(list_path)], check=True)
```

---

## 修改 8：统一导入风格

**严重程度**: 🟡 低优先  
**涉及文件**: `src/vector_db/__init__.py`, `src/main_agent.py`

### 问题描述

`src/` 内部 ~35 处导入已统一使用相对导入（`.` / `..`），但有 2 个文件例外，使用了绝对导入风格，与其他子包不一致。

### 8a. `src/vector_db/__init__.py` L3-5

```python
# 当前（绝对导入，与 rag/__init__.py、llm/__init__.py 等不一致）：
from vector_db.chroma_client import ChromaClient
from vector_db.embedding import EmbeddingModel
from vector_db.persistence import VectorStorePersistence

# 改为（相对导入，与其他所有子包 __init__.py 一致）：
from .chroma_client import ChromaClient
from .embedding import EmbeddingModel
from .persistence import VectorStorePersistence
```

### 8b. `src/main_agent.py` `ingest_knowledge()` 内部懒导入

```python
# 当前（绝对导入）：
from preprocessing.pdf_parser import PDFParser
from preprocessing.text_cleaner import TextCleaner
from preprocessing.chunker import Chunker

# 改为（相对导入，与同文件顶部的 from .rag.xxx / from .llm.xxx 一致）：
from .preprocessing.pdf_parser import PDFParser
from .preprocessing.text_cleaner import TextCleaner
from .preprocessing.chunker import Chunker
```

### 为什么要统一

- 当 `src/` 作为包（`from src.main_agent import ...`）导入时，绝对导入会触发 `ModuleNotFoundError`
- 相对导入是 Python 包内模块互引的标准做法
- 统一风格后可减少对 `pyrightconfig.json` 中 `extraPaths` 的依赖

> **注意**：`tests/` 和 `examples/` 中使用 `sys.path.insert(0, src/)` + 绝对导入是测试的标准做法，无需修改。

---

## 修改 9：清理遗留兼容代码

**严重程度**: 🟠 中优先  
**涉及文件**: `src/executor/ansible_runner.py`, `src/feedback/self_heal.py`, `tests/test_stage2.py`

### 问题描述

项目从旧的 `agent/` 包结构重构到当前 `src/` 结构后，残留了多处兼容旧结构的代码。这些代码引用的模块已不存在，导致功能实际无法使用。

### 9a. `src/executor/ansible_runner.py` — 4 个死函数（已在修改 6 覆盖）

由于 `from agent.hardening_agent import HardeningPlan, HardeningStep` 必然失败，以下 4 个函数永远无法正常运行（`HardeningPlan` / `HardeningStep` 为 `None`，调用 `.steps` / `.action` 等属性会报 `AttributeError`）：

| 函数 | 行号 | 说明 |
|------|------|------|
| `run_step()` | L267-L302 | 使用 `step.action`、`step.ansible_module`、`step.parameters` |
| `_create_step_playbook()` | L304-L334 | 使用 `step.action`、`step.ansible_module`、`step.parameters` |
| `run_hardening()` | L377-L408 | 遍历 `plan.steps`、访问 `plan.rule_id` |
| `execute_hardening_plan()` | L411-L454 | 遍历 `plan.steps`、访问 `plan.rule_id` |

**处理方式**：修改 6 中定义本地 dataclass 后，这些函数将恢复功能。

### 9b. `src/feedback/self_heal.py` L133 — 向后兼容路径

```python
# 向后兼容路径（无回调）
if self._is_fixed(analysis):
```

`heal()` 方法在未提供 `execute_fn` 回调时，退化为仅靠关键词判断 (`"fixed"`, `"resolved"` 等) 来猜测是否修复成功，而不实际重新执行。这是引入 `execute_fn` 回调机制之前遗留的旧逻辑。

**建议**：保留此路径但添加 `warnings.warn()` 提示调用方应传入 `execute_fn` 以获得可靠的自愈效果：

```python
# 向后兼容路径（无回调）
import warnings
warnings.warn(
    "heal() 未提供 execute_fn，将使用静态分析判断修复结果，建议传入 execute_fn 回调",
    DeprecationWarning,
    stacklevel=2
)
if self._is_fixed(analysis):
```

### 9c. `tests/test_stage2.py` — 完全引用旧模块

```python
# L28-35：引用不存在的旧模块
from agent.generator import (
    CodeGenerator,
    generate_ansible_code,
    validate_yaml,
    YAMLValidationError
)
from agent.rag_querier import RAGQuerier

# L140：
from agent.rag_querier import QueryResult
```

`agent.generator` 和 `agent.rag_querier` 模块**在当前项目中完全不存在**，这整个测试文件是旧架构的遗留物，无法运行。

**建议**：
- 如果测试用例仍有价值，重写导入以使用新架构模块（`src/llm/llm_client.py`、`src/rag/retriever.py` 等）
- 如果测试用例已过时，删除此文件或标记为 `@unittest.skip("待迁移到新架构")`

---

## 附录：给 Claude Code 的完整提示词

以下提示词可直接复制发送给 Claude Code 执行所有修改：

````
请按照以下优先级修改代码，使其与 codeplan/Full_Project_Spec.md 中的架构设计规范对齐。每完成一步验证无语法错误后再进行下一步。

## 前置：解决 Git 合并冲突

解决以下 13 个文件的合并冲突。每个文件只有 1 组冲突（<<<<<<< HEAD / ======= / >>>>>>>），保留 HEAD 版本（即 ======= 上方的内容），删除冲突标记和 ======= 下方的内容：

- examples/basic_usage.py
- tests/run_tests.py
- tests/test_stage2.py
- tests/data/__init__.py
- tests/integration/__init__.py
- tests/integration/test_main_agent.py
- tests/unit/__init__.py
- tests/unit/test_executor.py
- tests/unit/test_feedback.py
- tests/unit/test_llm.py
- tests/unit/test_preprocessing.py
- tests/unit/test_rag.py
- tests/unit/test_reporting.py

## 修改 1：实现知识回写闭环（架构图核心）

在 src/main_agent.py 的 harden() 方法中，当某条规则的 playbook 执行成功后，将成功的 playbook 内容和规则元数据通过 self.knowledge_store.add() 回写到向量数据库。这是架构图中"成功模式向量化存储 (Knowledge Update)"闭环的实现。

添加的内容类似：
```python
if execution_result.success:
    self.knowledge_store.add([{
        "content": playbook_content,
        "metadata": {
            "rule_id": rule_id,
            "type": "verified_playbook",
            "source": "self_execution",
            "target_host": target_host,
            "timestamp": datetime.now().isoformat()
        }
    }])
```

## 修改 2：集成 Ranker 到检索管线

在 src/rag/knowledge_store.py 中：
1. 导入 Ranker：`from rag.ranker import Ranker`
2. 在 __init__() 中初始化：`self.ranker = Ranker()`
3. 在 search() 中集成排序：先多取候选（n_results * 2），再用 ranker.rank() 排序取 top_k

## 修改 3：补全 CRUD 操作

在 src/vector_db/chroma_client.py 中新增：
- get(ids: List[str]) -> Dict：按 ID 查询
- update(ids, embeddings=None, documents=None, metadatas=None)：更新文档
- delete(ids: List[str])：按 ID 删除

在 src/rag/knowledge_store.py 中新增：
- get(item_id: str) -> Optional[Dict]：按 ID 获取，委托给 chroma_client.get()
- put(item_id: str, content: str, metadata=None)：更新/插入，先嵌入再 update
- delete(item_id: str)：删除，委托给 chroma_client.delete()

## 修改 4：加载 model_selector.yaml

在 src/llm/llm_client.py 中：
1. 添加 _load_model_config() 方法加载 configs/model_selector.yaml
2. 在 __init__() 中调用加载
3. generate() 方法增加 task_type 可选参数，根据配置动态选择模型

## 修改 5：集成 VectorStorePersistence

在 src/rag/knowledge_store.py 中：
1. 导入 VectorStorePersistence
2. 在 __init__() 中初始化
3. 在 add() 和 delete() 后调用 persistence.save_state()

## 修改 6：修复 HardeningPlan/HardeningStep 依赖

在 src/executor/ansible_runner.py 中：
1. 移除 L17-L20 对不存在的 agent.hardening_agent 的导入
2. 在文件内定义 HardeningStep 和 HardeningPlan 两个 dataclass

## 修改 7：小修复

1. src/vector_db/embedding.py：给 dimension property 添加 _dimension 缓存
2. src/vector_db/chroma_client.py：修复 clear() 方法——改为删除集合后重建
3. package.py L148：将 shell=True 的 tar 命令改为列表形式 subprocess.run(["tar", "-czf", ...], check=True)

## 修改 8：统一导入风格

1. src/vector_db/__init__.py L3-5：将 `from vector_db.xxx` 改为 `from .xxx`
2. src/main_agent.py ingest_knowledge() 内部：将 `from preprocessing.xxx` 改为 `from .preprocessing.xxx`

## 修改 9：清理遗留兼容代码

1. src/executor/ansible_runner.py：移除旧导入块 + 定义本地 dataclass（与修改 6 合并）
2. src/feedback/self_heal.py L133：向后兼容路径添加 DeprecationWarning
3. tests/test_stage2.py：重写导入以使用新架构，或标记 @unittest.skip

## 验证

完成所有修改后运行：
```bash
python3 -c "from src.main_agent import SecurityHardeningAgent; print('Import OK')"
python3 -m pytest tests/ -v
```
````

---

**注意**：以上修改建议均不涉及项目根目录结构变更或新文件创建（除 HardeningPlan/Step 内联定义外），是在现有代码基础上的增量修改。
