"""Security Hardening Framework with RAG and LLM.

A framework for automated security hardening using Retrieval-Augmented
Generation (RAG) and Large Language Models (LLM).
"""

# New modular architecture
from .preprocessing import PDFParser, TextCleaner, Chunker
from .vector_db import ChromaClient, EmbeddingModel, VectorStorePersistence
from .rag import Retriever, Ranker, KnowledgeStore, RetrievalResult, RankedResult
from .llm import LLMClient, PromptTemplate, SystemPrompt, LLMResponse
from .executor import AnsibleRunner, ExecutionResult, PlaybookBuilder, Task, SSHClient, SSHConfig, SSHResult
from .feedback import ResultParser, ErrorAnalyzer, SelfHealer
from .reporting import ReportGenerator, AuditLog

# Main agent
from .main_agent import SecurityHardeningAgent

__all__ = [
    # New modular architecture
    # Preprocessing
    "PDFParser",
    "TextCleaner",
    "Chunker",
    # Vector DB
    "ChromaClient",
    "EmbeddingModel",
    "VectorStorePersistence",
    # RAG
    "Retriever",
    "Ranker",
    "KnowledgeStore",
    "RetrievalResult",
    "RankedResult",
    # LLM
    "LLMClient",
    "PromptTemplate",
    "SystemPrompt",
    "LLMResponse",
    # Executor
    "AnsibleRunner",
    "ExecutionResult",
    "PlaybookBuilder",
    "Task",
    "SSHClient",
    "SSHConfig",
    "SSHResult",
    # Feedback
    "ResultParser",
    "ErrorAnalyzer",
    "SelfHealer",
    # Reporting
    "ReportGenerator",
    "AuditLog",
    # Main agent
    "SecurityHardeningAgent"
]
