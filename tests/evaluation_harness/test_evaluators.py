"""Tests for the ``func:`` handling in HTMLContentEvaluator.

Both ``func:`` sites used to splice page-derived values into eval(). A
single quote in the agent's final page URL closed the string literal and
the rest of the URL executed as Python inside the grading process (issues
#194 and #269). These tests pin the replacement behavior: helpers are
dispatched by name, arguments are literals parsed with ast.literal_eval,
page values are passed as arguments, and anything else raises ValueError.
"""

import ast
import json
import os
import sys
import types
from pathlib import Path
from typing import Any, Generator

import pytest
from playwright.sync_api import Page, sync_playwright

# browser_env.env_config asserts these URL env vars at import time. Dummy
# loopback hosts are enough because these tests never contact the sites.
os.environ.setdefault("REDDIT", "http://127.0.0.1:9999")
os.environ.setdefault("SHOPPING", "http://127.0.0.1:7770")
os.environ.setdefault("SHOPPING_ADMIN", "http://127.0.0.1:7780/admin")
os.environ.setdefault("GITLAB", "http://127.0.0.1:8023")
os.environ.setdefault("WIKIPEDIA", "http://127.0.0.1:8888/w/")
os.environ.setdefault("MAP", "http://127.0.0.1:3000")
os.environ.setdefault("HOMEPAGE", "http://127.0.0.1:3000")

# evaluation_harness imports openai.error, which only exists in openai<1.0
# (the version pinned in requirements.txt). Stub it when a newer client is
# installed so the evaluator can still be imported for testing.
import openai  # noqa: E402

if not hasattr(openai, "error"):
    _openai_error = types.ModuleType("openai.error")
    for _name in ("RateLimitError", "InvalidRequestError", "OpenAIError"):
        setattr(_openai_error, _name, type(_name, (Exception,), {}))
    openai.error = _openai_error
    sys.modules["openai.error"] = _openai_error

from browser_env.actions import create_stop_action  # noqa: E402
from evaluation_harness import evaluators as evaluators_module  # noqa: E402
from evaluation_harness.evaluators import (  # noqa: E402
    HTMLContentEvaluator,
)
from evaluation_harness.helper_functions import PseudoPage  # noqa: E402


@pytest.fixture(scope="function")
def chromium_page() -> Generator[Page, None, None]:
    """A real headless page so PseudoPage delegation behaves as in a run."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("about:blank")
        yield page
        browser.close()


def _write_config(tmp_path: Path, program_html: list[dict[str, Any]]) -> Path:
    config = {
        "task_id": 0,
        "intent": "test",
        "eval": {
            "eval_types": ["program_html"],
            "reference_answers": None,
            "reference_url": "",
            "program_html": program_html,
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    return config_file


def _run_evaluator(page: PseudoPage, config_file: Path) -> float:
    evaluator = HTMLContentEvaluator()
    return evaluator(
        trajectory=[create_stop_action("done")],
        config_file=str(config_file),
        page=page,
        client=None,
    )


def test_last_url_placeholder_is_passed_as_a_value(
    chromium_page: Page,
) -> None:
    """A benign final URL reaches reddit_get_post_url as plain data."""
    page = PseudoPage(
        chromium_page, "http://reddit.example/f/books/my-post/comments/abc"
    )
    result = evaluators_module._call_config_func(
        "reddit_get_post_url('__last_url__')", page
    )
    assert result == "http://reddit.example/f/books/my-post/"


def test_quote_bearing_final_url_is_not_executed(
    tmp_path: Path, chromium_page: Page
) -> None:
    """Regression for the eval() splice (issues #194 and #269).

    The payload URL below is what an agent could leave as its final page:
    the first quote used to close the string literal spliced into eval(),
    and the rest of the URL ran as Python in the grading process, writing
    two files. The evaluator must now deliver it to the helper as data and
    produce no side effects, whatever score or navigation error follows.
    """
    marker = tmp_path / "injected_marker"
    env_dump = tmp_path / "injected_env_dump"
    payload_url = (
        "http://127.0.0.1:9/f/books/1"
        + "'+str(open('"
        + str(marker)
        + "','w').write('pwned-by-agent-url'))"
        + "+str(open('"
        + str(env_dump)
        + "','w').write(str(__import__('os').environ)))+'"
    )
    config_file = _write_config(
        tmp_path,
        [
            {
                "url": "func:reddit_get_post_url('__last_url__')",
                "locator": (
                    "document.querySelector('.submission__inner').outerText"
                ),
                "required_contents": {"must_include": ["anything"]},
            }
        ],
    )
    try:
        _run_evaluator(PseudoPage(chromium_page, payload_url), config_file)
    except Exception:
        # navigating to the derived garbage URL fails; that is fine, the
        # point is that nothing executed
        pass
    assert not marker.exists()
    assert not env_dump.exists()


def test_unknown_func_name_raises(tmp_path: Path, chromium_page: Page) -> None:
    config_file = _write_config(
        tmp_path,
        [
            {
                "url": "func:execute_payload('touch /tmp/pwned')",
                "locator": "",
                "required_contents": {"must_include": ["anything"]},
            }
        ],
    )
    with pytest.raises(ValueError, match="Unknown func name"):
        _run_evaluator(PseudoPage(chromium_page, "http://x/"), config_file)


def test_non_literal_func_argument_raises(
    tmp_path: Path, chromium_page: Page
) -> None:
    config_file = _write_config(
        tmp_path,
        [
            {
                "url": "func:reddit_get_post_url(__import__('os').getcwd())",
                "locator": "",
                "required_contents": {"must_include": ["anything"]},
            }
        ],
    )
    with pytest.raises(ValueError, match="Invalid argument"):
        _run_evaluator(PseudoPage(chromium_page, "http://x/"), config_file)


def test_page_placeholder_dispatches_to_helper(
    tmp_path: Path, chromium_page: Page
) -> None:
    """gitlab locator funcs keep their behavior: "" for a missing account."""
    config_file = _write_config(
        tmp_path,
        [
            {
                "url": "last",
                "locator": (
                    "func:gitlab_get_project_memeber_role("
                    "__page__, 'nobody')"
                ),
                "required_contents": {"exact_match": ""},
            }
        ],
    )
    score = _run_evaluator(PseudoPage(chromium_page, "http://x/"), config_file)
    assert score == 1.0


def test_every_shipped_func_is_dispatchable() -> None:
    """The dispatch table must cover every func: in the shipped configs."""
    config_file = Path(__file__).parents[2] / "config_files" / "test.raw.json"
    tasks = json.loads(config_file.read_text())
    names = set()
    for task in tasks:
        for target in task["eval"]["program_html"]:
            for field in ("url", "locator"):
                value = target.get(field, "")
                if value.startswith("func:"):
                    expr = ast.parse(value.split("func:")[1], mode="eval").body
                    assert isinstance(expr, ast.Call)
                    assert isinstance(expr.func, ast.Name)
                    names.add(expr.func.id)
    registry = getattr(evaluators_module, "_CONFIG_FUNCS", None)
    assert registry is not None, "dispatch registry missing"
    assert names <= set(registry)
