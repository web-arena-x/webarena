"""Unit tests for MiniMax LLM provider."""

import argparse
import os
import re
from unittest.mock import MagicMock, patch

import pytest

from llms.lm_config import LMConfig, construct_llm_config
from llms.providers.minimax_utils import (
    MINIMAX_API_BASE,
    _get_minimax_headers,
    _strip_think_tags,
    generate_from_minimax_chat_completion,
)
from llms.tokenizers import Tokenizer
from llms.utils import call_llm


# ──────────────────────────────────────────────────────────────
# _strip_think_tags
# ──────────────────────────────────────────────────────────────
class TestStripThinkTags:
    def test_no_think_tags(self):
        assert _strip_think_tags("Hello world") == "Hello world"

    def test_single_think_block(self):
        text = "<think>some reasoning</think>Final answer"
        assert _strip_think_tags(text) == "Final answer"

    def test_multiline_think_block(self):
        text = "<think>\nstep 1\nstep 2\n</think>\nResult here"
        assert _strip_think_tags(text) == "Result here"

    def test_multiple_think_blocks(self):
        text = "<think>a</think>Hello <think>b</think>World"
        assert _strip_think_tags(text) == "Hello World"

    def test_empty_after_strip(self):
        text = "<think>only thinking</think>"
        assert _strip_think_tags(text) == ""


# ──────────────────────────────────────────────────────────────
# _get_minimax_headers
# ──────────────────────────────────────────────────────────────
class TestGetHeaders:
    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MINIMAX_API_KEY", None)
            with pytest.raises(ValueError, match="MINIMAX_API_KEY"):
                _get_minimax_headers()

    def test_returns_bearer_header(self):
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key-123"}):
            headers = _get_minimax_headers()
            assert headers["Authorization"] == "Bearer test-key-123"
            assert headers["Content-Type"] == "application/json"


# ──────────────────────────────────────────────────────────────
# construct_llm_config (minimax provider)
# ──────────────────────────────────────────────────────────────
class TestConstructLLMConfig:
    def _make_args(self, **overrides):
        defaults = dict(
            provider="minimax",
            model="MiniMax-M2.7",
            mode="chat",
            temperature=0.8,
            top_p=0.9,
            context_length=0,
            max_tokens=384,
            stop_token=None,
            max_obs_length=1920,
            max_retry=1,
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def test_minimax_config_basic(self):
        args = self._make_args()
        config = construct_llm_config(args)
        assert config.provider == "minimax"
        assert config.model == "MiniMax-M2.7"
        assert config.mode == "chat"
        assert config.gen_config["temperature"] == 0.8
        assert config.gen_config["max_tokens"] == 384

    def test_minimax_config_fields(self):
        args = self._make_args(temperature=0.5, top_p=0.95, max_tokens=512)
        config = construct_llm_config(args)
        assert config.gen_config["top_p"] == 0.95
        assert config.gen_config["max_tokens"] == 512
        assert config.gen_config["max_obs_length"] == 1920

    def test_unknown_provider_raises(self):
        args = self._make_args(provider="unknown")
        with pytest.raises(NotImplementedError):
            construct_llm_config(args)


# ──────────────────────────────────────────────────────────────
# generate_from_minimax_chat_completion (mocked HTTP)
# ──────────────────────────────────────────────────────────────
class TestGenerateMinimax:
    @patch("llms.providers.minimax_utils.requests.post")
    def test_basic_generation(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "click [42]"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            result = generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="MiniMax-M2.7",
                temperature=0.8,
                max_tokens=384,
                top_p=0.9,
                context_length=0,
            )

        assert result == "click [42]"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert MINIMAX_API_BASE in call_args[0][0]

    @patch("llms.providers.minimax_utils.requests.post")
    def test_think_tags_stripped(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "<think>reasoning</think>click [10]"
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            result = generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "test"}],
                model="MiniMax-M2.7",
                temperature=0.8,
                max_tokens=384,
                top_p=0.9,
                context_length=0,
            )

        assert result == "click [10]"

    @patch("llms.providers.minimax_utils.requests.post")
    def test_temperature_clamping(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "test"}],
                model="MiniMax-M2.7",
                temperature=2.0,  # should be clamped to 1.0
                max_tokens=384,
                top_p=0.9,
                context_length=0,
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["temperature"] == 1.0

    @patch("llms.providers.minimax_utils.requests.post")
    def test_stop_token_passed(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "result"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "test"}],
                model="MiniMax-M2.7",
                temperature=0.5,
                max_tokens=384,
                top_p=0.9,
                context_length=0,
                stop_token="```",
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["stop"] == ["```"]

    @patch("llms.providers.minimax_utils.requests.post")
    def test_no_stop_token(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "result"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "test"}],
                model="MiniMax-M2.7",
                temperature=0.5,
                max_tokens=384,
                top_p=0.9,
                context_length=0,
            )

        payload = mock_post.call_args[1]["json"]
        assert "stop" not in payload


# ──────────────────────────────────────────────────────────────
# call_llm dispatch (minimax)
# ──────────────────────────────────────────────────────────────
class TestCallLLMMinimax:
    @patch("llms.utils.generate_from_minimax_chat_completion")
    def test_dispatch_minimax_chat(self, mock_gen):
        mock_gen.return_value = "click [5]"
        config = LMConfig(provider="minimax", model="MiniMax-M2.7", mode="chat")
        config.gen_config["temperature"] = 0.8
        config.gen_config["top_p"] = 0.9
        config.gen_config["context_length"] = 0
        config.gen_config["max_tokens"] = 384

        messages = [{"role": "user", "content": "test prompt"}]
        result = call_llm(config, messages)

        assert result == "click [5]"
        mock_gen.assert_called_once_with(
            messages=messages,
            model="MiniMax-M2.7",
            temperature=0.8,
            top_p=0.9,
            context_length=0,
            max_tokens=384,
            stop_token=None,
        )

    def test_dispatch_minimax_completion_raises(self):
        config = LMConfig(
            provider="minimax", model="MiniMax-M2.7", mode="completion"
        )
        config.gen_config["temperature"] = 0.8
        with pytest.raises(ValueError, match="chat mode"):
            call_llm(config, "some prompt")


# ──────────────────────────────────────────────────────────────
# Tokenizer (minimax)
# ──────────────────────────────────────────────────────────────
class TestTokenizerMinimax:
    def test_minimax_tokenizer_encode_decode(self):
        tokenizer = Tokenizer("minimax", "MiniMax-M2.7")
        text = "Hello, world!"
        tokens = tokenizer.encode(text)
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        decoded = tokenizer.decode(tokens)
        assert decoded == text

    def test_minimax_tokenizer_callable(self):
        tokenizer = Tokenizer("minimax", "MiniMax-M2.7")
        tokens = tokenizer("Test input")
        assert isinstance(tokens, list)
        assert len(tokens) > 0


# ──────────────────────────────────────────────────────────────
# PromptConstructor (minimax provider)
# ──────────────────────────────────────────────────────────────
_ENV_URLS = {
    "REDDIT": "http://reddit.test",
    "SHOPPING": "http://shopping.test",
    "SHOPPING_ADMIN": "http://shopping-admin.test",
    "GITLAB": "http://gitlab.test",
    "WIKIPEDIA": "http://wikipedia.test",
    "MAP": "http://map.test",
    "HOMEPAGE": "http://homepage.test",
}


class TestPromptConstructorMinimax:
    @patch.dict(os.environ, _ENV_URLS)
    def test_minimax_uses_chat_format(self):
        """MiniMax provider should produce the same chat message format as OpenAI."""
        # Reload env_config to pick up the env vars, then import
        import importlib
        import browser_env.env_config as env_config
        importlib.reload(env_config)
        from agent.prompts.prompt_constructor import PromptConstructor

        config = LMConfig(provider="minimax", model="MiniMax-M2.7", mode="chat")
        tokenizer = Tokenizer("minimax", "MiniMax-M2.7")

        pc = PromptConstructor.__new__(PromptConstructor)
        pc.lm_config = config
        pc.tokenizer = tokenizer

        intro = "You are a helpful assistant."
        examples = [("obs1", "action1")]
        current = "Current observation"

        result = pc.get_lm_api_input(intro, examples, current)
        assert isinstance(result, list)
        assert result[0]["role"] == "system"
        assert result[0]["content"] == intro
        assert result[-1]["role"] == "user"
        assert result[-1]["content"] == current

    @patch.dict(os.environ, _ENV_URLS)
    def test_minimax_unsupported_mode_raises(self):
        """Modes other than chat/completion should raise for minimax."""
        import importlib
        import browser_env.env_config as env_config
        importlib.reload(env_config)
        from agent.prompts.prompt_constructor import PromptConstructor

        config = LMConfig(
            provider="minimax", model="MiniMax-M2.7", mode="invalid_mode"
        )
        tokenizer = Tokenizer("minimax", "MiniMax-M2.7")

        pc = PromptConstructor.__new__(PromptConstructor)
        pc.lm_config = config
        pc.tokenizer = tokenizer

        with pytest.raises(ValueError, match="do not support mode"):
            pc.get_lm_api_input("intro", [], "current")


# ──────────────────────────────────────────────────────────────
# API base URL
# ──────────────────────────────────────────────────────────────
class TestAPIConstants:
    def test_api_base_url(self):
        assert MINIMAX_API_BASE == "https://api.minimax.io/v1"

    @patch("llms.providers.minimax_utils.requests.post")
    def test_correct_endpoint_called(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="MiniMax-M2.7",
                temperature=0.5,
                max_tokens=100,
                top_p=0.9,
                context_length=0,
            )

        url = mock_post.call_args[0][0]
        assert url == "https://api.minimax.io/v1/chat/completions"


# ──────────────────────────────────────────────────────────────
# Model names
# ──────────────────────────────────────────────────────────────
class TestModelNames:
    @patch("llms.providers.minimax_utils.requests.post")
    def test_m27_model(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="MiniMax-M2.7",
                temperature=0.5,
                max_tokens=100,
                top_p=0.9,
                context_length=0,
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "MiniMax-M2.7"

    @patch("llms.providers.minimax_utils.requests.post")
    def test_m25_highspeed_model(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="MiniMax-M2.5-highspeed",
                temperature=0.5,
                max_tokens=100,
                top_p=0.9,
                context_length=0,
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "MiniMax-M2.5-highspeed"


# ──────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────
class TestEdgeCases:
    @patch("llms.providers.minimax_utils.requests.post")
    def test_zero_temperature(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="MiniMax-M2.7",
                temperature=0.0,
                max_tokens=100,
                top_p=0.9,
                context_length=0,
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["temperature"] == 0.0

    @patch("llms.providers.minimax_utils.requests.post")
    def test_negative_temperature_clamped(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            generate_from_minimax_chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="MiniMax-M2.7",
                temperature=-0.5,
                max_tokens=100,
                top_p=0.9,
                context_length=0,
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["temperature"] == 0.0

    @patch("llms.providers.minimax_utils.requests.post")
    def test_multi_message_conversation(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a web agent."},
            {"role": "system", "name": "example_user", "content": "obs"},
            {"role": "system", "name": "example_assistant", "content": "act"},
            {"role": "user", "content": "current observation"},
        ]

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}):
            result = generate_from_minimax_chat_completion(
                messages=messages,
                model="MiniMax-M2.7",
                temperature=0.8,
                max_tokens=384,
                top_p=0.9,
                context_length=0,
            )

        assert result == "response"
        payload = mock_post.call_args[1]["json"]
        assert len(payload["messages"]) == 4
