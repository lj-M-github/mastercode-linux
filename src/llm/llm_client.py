"""LLM Client module - Interface to LLM providers."""

import os
import yaml
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Union

# 加载 .env 文件中的环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM 客户端。

    提供与大语言模型的接口，支持 OpenAI 等提供商。

    Attributes:
        model: 模型名称
        api_key: API 密钥
        temperature: 温度参数
        client: API 客户端

    Examples:
        >>> client = LLMClient("deepseek-chat")
        >>> response = client.generate("Hello, how are you?")
        >>> print(response.content)
    """

    DEFAULT_MODEL = "deepseek-chat"
    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_TEMPERATURE = 0.1
    DEFAULT_MAX_TOKENS = 1000

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        model_config_path: Optional[str] = None
    ):
        """初始化 LLM 客户端。

        Args:
            model: 模型名称
            api_key: API 密钥（默认从环境变量读取）
            base_url: API 基础地址
            temperature: 温度参数
            model_config_path: 模型配置文件路径（可选）
        """
        self.model = model
        self.temperature = temperature
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or self.DEFAULT_BASE_URL

        # 加载模型配置
        self.model_config = self._load_model_config(model_config_path)

        self._init_client()

    def _load_model_config(self, path: Optional[str]) -> Dict[str, Any]:
        """加载模型配置文件。

        Args:
            path: 配置文件路径

        Returns:
            配置字典，如果文件不存在则返回空字典
        """
        if not path:
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError as e:
            logger.warning(f"YAML 解析错误：{e}")
            return {}

    def _init_client(self) -> None:
        """初始化客户端。"""
        if OPENAI_AVAILABLE and self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        task_type: Optional[str] = None
    ) -> "LLMResponse":
        """生成响应。

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            max_tokens: 最大 token 数
            temperature: 温度参数
            task_type: 任务类型（如 code_generation、error_analysis）

        Returns:
            LLMResponse 对象
        """
        # 根据任务类型动态选择模型
        model_to_use = self._select_model_for_task(task_type)

        max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else self.temperature

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=model_to_use,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        )

    def _select_model_for_task(self, task_type: Optional[str]) -> str:
        """根据任务类型选择模型。

        Args:
            task_type: 任务类型

        Returns:
            模型名称
        """
        if not task_type or not self.model_config:
            return self.model

        models_config = self.model_config.get("models", {})
        if task_type in models_config:
            task_cfg = models_config[task_type]
            # 同步更新温度参数
            if "temperature" in task_cfg:
                self.temperature = task_cfg["temperature"]
            return task_cfg.get("model", self.model)
        return self.model

    def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        max_workers: int = 5
    ) -> List["LLMResponse"]:
        """批量生成响应（并发执行）。

        Args:
            prompts: 提示词列表
            system_prompt: 系统提示词
            max_workers: 最大并发线程数，默认 5

        Returns:
            LLMResponse 对象列表

        注意:
            使用 ThreadPoolExecutor 并发执行 API 请求，
            可以显著提高批量生成的速度。
        """
        def generate_single(prompt: str) -> LLMResponse:
            return self.generate(prompt, system_prompt)

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_prompt = {executor.submit(generate_single, prompt): i
                               for i, prompt in enumerate(prompts)}

            # 按原始顺序收集结果
            results = [None] * len(prompts)
            for future in as_completed(future_to_prompt):
                index = future_to_prompt[future]
                results[index] = future.result()

        return results

    @property
    def is_available(self) -> bool:
        """检查 LLM 是否可用。"""
        return self.client is not None


class LLMResponse:
    """LLM 响应数据类。

    Attributes:
        content: 响应内容
        model: 使用的模型
        usage: 使用统计
    """
    def __init__(
        self,
        content: str,
        model: str,
        usage: Dict[str, int]
    ):
        self.content = content
        self.model = model
        self.usage = usage

    def __str__(self) -> str:
        return self.content
