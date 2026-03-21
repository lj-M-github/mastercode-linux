"""单元测试 - LLM 模块."""

import os
from unittest.mock import patch, MagicMock
import pytest

from src.llm.llm_client import LLMClient, LLMResponse
from src.llm.prompt_templates import PromptTemplate, SystemPrompt


class TestLLMClient:
    """LLMClient 测试类。"""

    def test_init_without_api_key(self):
        """测试无 API Key 初始化。"""
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient(api_key=None)
            assert not client.is_available

    def test_generate_mock(self):
        """测试生成模拟响应。"""
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient(api_key=None)
            response = client.generate("test prompt")
            assert isinstance(response, LLMResponse)
            assert "Mock" in response.content

    def test_generate_batch(self):
        """测试批量生成。"""
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient(api_key=None)
            responses = client.generate_batch(["prompt1", "prompt2"])
            assert len(responses) == 2


class TestLLMResponse:
    """LLMResponse 测试类。"""

    def test_str(self):
        """测试字符串表示。"""
        response = LLMResponse(
            content="test content",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )
        assert str(response) == "test content"


class TestPromptTemplate:
    """PromptTemplate 测试类。"""

    @pytest.fixture
    def template(self):
        """测试前准备。"""
        return PromptTemplate("Hello, {name}!")

    def test_format(self, template):
        """测试格式化。"""
        result = template.format(name="World")
        assert result == "Hello, World!"

    def test_validate_success(self, template):
        """测试验证成功。"""
        result = template.validate(name="World")
        assert result is True

    def test_validate_failure(self, template):
        """测试验证失败。"""
        result = template.validate()
        assert result is False

    def test_extract_variables(self):
        """测试提取变量。"""
        template = PromptTemplate("Hello {name}, you are {age} years old")
        assert template.variables == ["name", "age"]


class TestSystemPrompt:
    """SystemPrompt 测试类。"""

    def test_build_basic(self):
        """测试构建基础提示词。"""
        prompt = SystemPrompt(role="You are a helper")
        result = prompt.build()
        assert result == "You are a helper"

    def test_build_with_constraints(self):
        """测试构建带约束的提示词。"""
        prompt = SystemPrompt(
            role="You are a helper",
            constraints=["Be kind", "Be helpful"]
        )
        result = prompt.build()
        assert "Be kind" in result
        assert "Be helpful" in result

    def test_build_with_output_format(self):
        """测试构建带输出格式的提示词。"""
        prompt = SystemPrompt(
            role="You are a helper",
            output_format="JSON format"
        )
        result = prompt.build()
        assert "JSON format" in result
