"""Tools to generate from MiniMax prompts via OpenAI-compatible API."""

import asyncio
import logging
import os
import random
import re
import time
from typing import Any

import aiolimiter
import requests
from tqdm.asyncio import tqdm_asyncio

MINIMAX_API_BASE = "https://api.minimax.io/v1"


def _get_minimax_headers() -> dict[str, str]:
    """Return authorization headers for MiniMax API."""
    if "MINIMAX_API_KEY" not in os.environ:
        raise ValueError(
            "MINIMAX_API_KEY environment variable must be set when using MiniMax API."
        )
    return {
        "Authorization": f"Bearer {os.environ['MINIMAX_API_KEY']}",
        "Content-Type": "application/json",
    }


def _strip_think_tags(text: str) -> str:
    """Strip <think>...</think> blocks from model output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def retry_with_exponential_backoff(  # type: ignore
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 3,
    errors: tuple[Any] = (requests.exceptions.RequestException,),
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):  # type: ignore
        num_retries = 0
        delay = initial_delay
        while True:
            try:
                return func(*args, **kwargs)
            except errors as e:
                num_retries += 1
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )
                delay *= exponential_base * (1 + jitter * random.random())
                logging.warning(f"Retrying in {delay:.1f} seconds: {e}")
                time.sleep(delay)
            except Exception as e:
                raise e

    return wrapper


@retry_with_exponential_backoff
def generate_from_minimax_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    stop_token: str | None = None,
) -> str:
    """Generate from MiniMax Chat Completion API (OpenAI-compatible).

    Args:
        messages: List of message dicts with 'role' and 'content'.
        model: MiniMax model name (e.g., 'MiniMax-M2.7').
        temperature: Sampling temperature. Clamped to [0.01, 1.0] for MiniMax.
        max_tokens: Maximum number of tokens to generate.
        top_p: Top-p sampling parameter.
        context_length: Context length (unused, kept for API compatibility).
        stop_token: Optional stop token.

    Returns:
        Generated text response.
    """
    headers = _get_minimax_headers()

    # MiniMax temperature range: [0, 1.0]
    clamped_temperature = max(0.0, min(temperature, 1.0))

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": clamped_temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
    }
    if stop_token:
        payload["stop"] = [stop_token]

    response = requests.post(
        f"{MINIMAX_API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    answer: str = data["choices"][0]["message"]["content"]
    return _strip_think_tags(answer)


async def _throttled_minimax_chat_completion(
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    top_p: float,
    limiter: aiolimiter.AsyncLimiter,
) -> dict[str, Any]:
    """Throttled async MiniMax chat completion."""
    import aiohttp

    headers = _get_minimax_headers()
    clamped_temperature = max(0.0, min(temperature, 1.0))

    payload = {
        "model": model,
        "messages": messages,
        "temperature": clamped_temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
    }

    async with limiter:
        for _ in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{MINIMAX_API_BASE}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=120),
                    ) as resp:
                        if resp.status == 429:
                            logging.warning(
                                "MiniMax API rate limit exceeded. Sleeping for 10 seconds."
                            )
                            await asyncio.sleep(10)
                            continue
                        resp.raise_for_status()
                        return await resp.json()
            except asyncio.TimeoutError:
                logging.warning("MiniMax API timeout. Sleeping for 10 seconds.")
                await asyncio.sleep(10)
            except Exception as e:
                logging.warning(f"MiniMax API error: {e}")
                break
        return {"choices": [{"message": {"content": ""}}]}


async def agenerate_from_minimax_chat_completion(
    messages_list: list[list[dict[str, str]]],
    engine: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    requests_per_minute: int = 60,
) -> list[str]:
    """Generate from MiniMax Chat Completion API (async, batch).

    Args:
        messages_list: List of message lists.
        engine: MiniMax model name.
        temperature: Sampling temperature.
        max_tokens: Maximum number of tokens to generate.
        top_p: Top-p sampling parameter.
        context_length: Context length (unused).
        requests_per_minute: Rate limit.

    Returns:
        List of generated responses.
    """
    limiter = aiolimiter.AsyncLimiter(requests_per_minute)
    async_responses = [
        _throttled_minimax_chat_completion(
            model=engine,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            limiter=limiter,
        )
        for messages in messages_list
    ]
    responses = await tqdm_asyncio.gather(*async_responses)
    return [
        _strip_think_tags(x["choices"][0]["message"]["content"])
        for x in responses
    ]
