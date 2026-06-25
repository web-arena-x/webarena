import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


sys.modules.setdefault(
    "aiolimiter",
    types.SimpleNamespace(AsyncLimiter=lambda *args, **kwargs: None),
)
openai_stub = sys.modules.setdefault("openai", types.ModuleType("openai"))
openai_error_stub = sys.modules.setdefault("openai.error", types.ModuleType("openai.error"))
setattr(openai_error_stub, "APIError", RuntimeError)
setattr(openai_error_stub, "RateLimitError", RuntimeError)
setattr(openai_stub, "error", openai_error_stub)
sys.modules.setdefault("tqdm", types.ModuleType("tqdm"))
tqdm_asyncio_stub = sys.modules.setdefault("tqdm.asyncio", types.ModuleType("tqdm.asyncio"))
setattr(tqdm_asyncio_stub, "tqdm_asyncio", lambda items, **kwargs: items)

OPENAI_UTILS_PATH = ROOT / "llms" / "providers" / "openai_utils.py"
spec = importlib.util.spec_from_file_location("webarena_openai_utils_for_test", OPENAI_UTILS_PATH)
openai_utils = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(openai_utils)


JUDGE_ENV_KEYS = {
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "QWEN_API_KEY",
    "QWEN_BASE_URL",
    "QWEN_GRADER_API_KEY",
    "QWEN_GRADER_BASE_URL",
    "WEBARENA_JUDGE_API_KEY",
    "WEBARENA_JUDGE_BASE_URL",
}


@pytest.fixture(autouse=True)
def clean_judge_env(monkeypatch: pytest.MonkeyPatch):
    for key in JUDGE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    openai_utils.openai.api_key = ""
    openai_utils.openai.api_base = ""


def test_openrouter_judge_ignores_qwen_and_openai_route_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEN_API_KEY", "qwen-key")
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope.example.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.example.test/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    openai_utils._configure_chat_provider("qwen/qwen3.7-max")

    assert openai_utils.openai.api_key == "openrouter-key"
    assert openai_utils.openai.api_base == "https://openrouter.ai/api/v1"


def test_openai_key_alone_does_not_configure_qwen_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    with pytest.raises(ValueError, match="Qwen3.7 Max judge calls need"):
        openai_utils._configure_chat_provider("qwen3.7-max")
