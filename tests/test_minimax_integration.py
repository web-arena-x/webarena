"""Integration tests for MiniMax LLM provider.

These tests call the real MiniMax API and require MINIMAX_API_KEY to be set.
Skip automatically when the key is not available.
"""

import os

import pytest

from llms.providers.minimax_utils import generate_from_minimax_chat_completion

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY")
skip_no_key = pytest.mark.skipif(
    not MINIMAX_API_KEY, reason="MINIMAX_API_KEY not set"
)


@skip_no_key
class TestMiniMaxIntegration:
    def test_basic_chat_completion(self):
        """Test a simple chat completion against the real API."""
        messages = [
            {"role": "user", "content": "Reply with exactly: HELLO_WEBARENA"},
        ]
        result = generate_from_minimax_chat_completion(
            messages=messages,
            model="MiniMax-M2.7",
            temperature=0.01,
            max_tokens=256,
            top_p=0.9,
            context_length=0,
        )
        assert "HELLO_WEBARENA" in result

    def test_system_message(self):
        """Test that system messages are handled correctly."""
        messages = [
            {
                "role": "system",
                "content": "You are a web navigation agent. Always respond with an action in the format: click [id]",
            },
            {
                "role": "user",
                "content": "Click the search button with id 42.",
            },
        ]
        result = generate_from_minimax_chat_completion(
            messages=messages,
            model="MiniMax-M2.7",
            temperature=0.01,
            max_tokens=256,
            top_p=0.9,
            context_length=0,
        )
        assert len(result) > 0

    def test_think_tags_stripped_in_response(self):
        """Verify that any <think> tags in the response are stripped."""
        messages = [
            {"role": "user", "content": "Say exactly: TEST_OUTPUT"},
        ]
        result = generate_from_minimax_chat_completion(
            messages=messages,
            model="MiniMax-M2.7",
            temperature=0.01,
            max_tokens=256,
            top_p=0.9,
            context_length=0,
        )
        assert "<think>" not in result
        assert "</think>" not in result
