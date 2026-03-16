"""LLM Client module - Interface to LLM providers."""

import os
from typing import List, Dict, Any, Optional, Union

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


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
        temperature: float = DEFAULT_TEMPERATURE
    ):
        """初始化 LLM 客户端。

        Args:
            model: 模型名称
            api_key: API 密钥（默认从环境变量读取）
            base_url: API 基础地址
            temperature: 温度参数
        """
        self.model = model
        self.temperature = temperature
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url or self.DEFAULT_BASE_URL

        self._init_client()

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
        temperature: Optional[float] = None
    ) -> "LLMResponse":
        """生成响应。

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            max_tokens: 最大 token 数
            temperature: 温度参数

        Returns:
            LLMResponse 对象
        """
        if self.client is None:
            return self._mock_response(prompt)

        max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else self.temperature

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        )

    def _mock_response(self, prompt: str) -> "LLMResponse":
        """生成模拟响应（无 API Key 时）。

        Args:
            prompt: 提示词

        Returns:
            模拟响应
        """
        return LLMResponse(
            content=f"[Mock Response] Received: {prompt[:100]}...",
            model="mock",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )

    def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None
    ) -> List["LLMResponse"]:
        """批量生成响应。

        Args:
            prompts: 提示词列表
            system_prompt: 系统提示词

        Returns:
            LLMResponse 对象列表
        """
        return [self.generate(prompt, system_prompt) for prompt in prompts]

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
