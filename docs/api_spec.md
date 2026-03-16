# API Specification

## Core Classes and Functions

### Preprocessing Module

#### PDFParser
```python
class PDFParser:
    def __init__(self, pdf_path: str)
    def extract_text() -> List[Tuple[int, str]]
    def get_page_text(page_num: int) -> str
    @property
    def num_pages() -> int
```

#### TextCleaner
```python
class TextCleaner:
    def __init__()
    def clean(text: str) -> str
    def normalize_whitespace(text: str) -> str
```

#### Chunker
```python
class Chunker:
    def __init__(chunk_size: int = 800, chunk_overlap: int = 100)
    def split(text: str, metadata: Dict = None) -> List[TextChunk]
    def split_with_context(text: str, context: Dict, id_prefix: str = "") -> List[TextChunk]
```

### Vector DB Module

#### ChromaClient
```python
class ChromaClient:
    def __init__(db_path: str, collection_name: str)
    def add(ids: List[str], embeddings: List[List[float]], documents: List[str], metadatas: List[Dict])
    def query(query_embeddings: List[List[float]], n_results: int, where: Dict) -> Dict
    def get_collection_info() -> Dict
    def clear()
```

#### EmbeddingModel
```python
class EmbeddingModel:
    def __init__(model_name: str = "all-MiniLM-L6-v2")
    def encode(texts: List[str], show_progress: bool = False) -> List[List[float]]
    def encode_single(text: str) -> List[float]
    @property
    def dimension() -> int
```

### RAG Module

#### Retriever
```python
class Retriever:
    def __init__(chroma_client: ChromaClient, embedding_model: EmbeddingModel)
    def search(query: str, n_results: int, filter_dict: Dict) -> List[RetrievalResult]
    def search_by_embedding(embedding: List[float], n_results: int, filter_dict: Dict) -> List[RetrievalResult]
```

#### Ranker
```python
class Ranker:
    def __init__()
    def rank(results: List, query: str, top_k: int = None) -> List[RankedResult]
    def filter_by_metadata(results: List, metadata_filter: Dict) -> List
    def boost_by_relevance(results: List, query: str, boost_fields: List) -> List[RankedResult]
```

#### KnowledgeStore
```python
class KnowledgeStore:
    def __init__(db_path: str, collection_name: str, model_name: str)
    def add(items: List[Dict], show_progress: bool = False) -> int
    def search(query: str, n_results: int, filter_dict: Dict) -> List[RetrievalResult]
    def get_stats() -> Dict
    def clear()
```

### LLM Module

#### LLMClient
```python
class LLMClient:
    def __init__(model: str, api_key: str, temperature: float)
    def generate(prompt: str, system_prompt: str, max_tokens: int, temperature: float) -> LLMResponse
    def generate_batch(prompts: List[str], system_prompt: str) -> List[LLMResponse]
    @property
    def is_available() -> bool
```

#### PromptTemplate
```python
class PromptTemplate:
    def __init__(template: str)
    def format(**kwargs) -> str
    def validate(** kwargs) -> bool
```

### Executor Module

#### AnsibleRunner
```python
class AnsibleRunner:
    def __init__(playbook_dir: str, verbose: bool)
    def run_playbook(playbook_name: str, extra_vars: Dict, limit: str) -> ExecutionResult
    def execute(playbook_content: str, target_host: str) -> ExecutionResult
    def run_step(step: HardeningStep, target_host: str) -> ExecutionResult
```

#### PlaybookBuilder
```python
class PlaybookBuilder:
    def __init__(name: str, hosts: str, become: bool, gather_facts: bool)
    def add_task(name: str, module: str, params: Dict, when: str, register: str) -> PlaybookBuilder
    def build() -> str
    def save(filepath: str) -> str
```

#### SSHClient
```python
class SSHClient:
    def __init__(config: SSHConfig)
    def connect() -> bool
    def disconnect()
    def execute(command: str, timeout: int) -> SSHResult
    def upload(local_path: str, remote_path: str) -> bool
    def download(remote_path: str, local_path: str) -> bool
```

### Feedback Module

#### ResultParser
```python
class ResultParser:
    def __init__()
    def parse(output: str, task_id: str) -> ExecutionResult
    def parse_json(json_output: str) -> ExecutionResult
    def get_feedback_dict(result: ExecutionResult) -> Dict
```

#### ErrorAnalyzer
```python
class ErrorAnalyzer:
    def __init__(llm_client: LLMClient)
    def analyze(error_message: str, playbook_content: str) -> ErrorAnalysis
    def batch_analyze(errors: List[Dict]) -> List[ErrorAnalysis]
```

#### SelfHealer
```python
class SelfHealer:
    def __init__(llm_client: LLMClient, max_retries: int)
    def heal(original_playbook: str, error_log: str, original_rule: str) -> HealingResult
    def can_retry(error: str) -> bool
    def get_healing_stats(results: List[HealingResult]) -> Dict
```

### Reporting Module

#### ReportGenerator
```python
class ReportGenerator:
    def __init__(report_dir: str, report_format: str)
    def add_entry(entry: ReportEntry)
    def add_result(rule_id: str, status: str, description: str, details: Dict)
    def generate(report_name: str) -> str
    def clear()
```

#### AuditLog
```python
class AuditLog:
    def __init__(log_dir: str)
    def log_action(action_type: str, details: Dict, result: str)
    def log_execution(rule_id: str, playbook: str, result: str, output: str)
    def log_query(query: str, results_count: int, cloud_provider: str)
    def log_error(error_type: str, error_message: str, context: Dict)
    def get_history(rule_id: str, action_type: str, limit: int) -> List[Dict]
    def get_statistics() -> Dict
```

### Main Agent

#### SecurityHardeningAgent
```python
class SecurityHardeningAgent:
    def __init__(config: Dict)
    def ingest_knowledge(doc_dir: str) -> Dict
    def search_knowledge(query: str, n_results: int, cloud_provider: str) -> List[Dict]
    def generate_playbook(rule_id: str, section_title: str, remediation: str, cloud_provider: str) -> str
    def harden(query: str, target_host: str, enable_self_heal: bool) -> Dict
    def generate_report(report_name: str) -> str
    def get_stats() -> Dict
```
