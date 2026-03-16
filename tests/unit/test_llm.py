"""单元测试 - LLM 模块."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from llm.llm_client import LLMClient, LLMResponse
from llm.prompt_templates import PromptTemplate, SystemPrompt


class TestLLMClient(unittest.TestCase):
    """LLMClient 测试类。"""

    def test_init_without_api_key(self):
        """测试无 API Key 初始化。"""
        client = LLMClient(api_key=None)
        self.assertFalse(client.is_available)

    def test_generate_mock(self):
        """测试生成模拟响应。"""
        client = LLMClient(api_key=None)
        response = client.generate("test prompt")
        self.assertIsInstance(response, LLMResponse)
        self.assertIn("Mock", response.content)

    def test_generate_batch(self):
        """测试批量生成。"""
        client = LLMClient(api_key=None)
        responses = client.generate_batch(["prompt1", "prompt2"])
        self.assertEqual(len(responses), 2)


class TestLLMResponse(unittest.TestCase):
    """LLMResponse 测试类。"""

    def test_str(self):
        """测试字符串表示。"""
        response = LLMResponse(
            content="test content",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )
        self.assertEqual(str(response), "test content")


class TestPromptTemplate(unittest.TestCase):
    """PromptTemplate 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.template = PromptTemplate("Hello, {name}!")

    def test_format(self):
        """测试格式化。"""
        result = self.template.format(name="World")
        self.assertEqual(result, "Hello, World!")

    def test_validate_success(self):
        """测试验证成功。"""
        result = self.template.validate(name="World")
        self.assertTrue(result)

    def test_validate_failure(self):
        """测试验证失败。"""
        result = self.template.validate()
        self.assertFalse(result)

    def test_extract_variables(self):
        """测试提取变量。"""
        template = PromptTemplate("Hello {name}, you are {age} years old")
        self.assertEqual(template.variables, ["name", "age"])


class TestSystemPrompt(unittest.TestCase):
    """SystemPrompt 测试类。"""

    def test_build_basic(self):
        """测试构建基础提示词。"""
        prompt = SystemPrompt(role="You are a helper")
        result = prompt.build()
        self.assertEqual(result, "You are a helper")

    def test_build_with_constraints(self):
        """测试构建带约束的提示词。"""
        prompt = SystemPrompt(
            role="You are a helper",
            constraints=["Be kind", "Be helpful"]
        )
        result = prompt.build()
        self.assertIn("Be kind", result)
        self.assertIn("Be helpful", result)

    def test_build_with_output_format(self):
        """测试构建带输出格式的提示词。"""
        prompt = SystemPrompt(
            role="You are a helper",
            output_format="JSON format"
        )
        result = prompt.build()
        self.assertIn("JSON format", result)


if __name__ == "__main__":
    unittest.main()
