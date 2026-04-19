"""LLM provider abstraction for async file summarization."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Protocol


class LLMProvider(Protocol):
    async def summarize(
        self,
        file_path: str,
        file_content: str,
        model: str,
        api_key: str | None,
        base_url: str | None,
        max_tokens: int,
    ) -> str: ...


@dataclass(frozen=True)
class OpenAIProvider:
    async def summarize(
        self,
        file_path: str,
        file_content: str,
        model: str,
        api_key: str | None,
        base_url: str | None,
        max_tokens: int,
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"), base_url=base_url)
        response = await client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Summarize this file in 2-4 concise lines. File: {file_path}\n\n"
                        f"{file_content[:8000]}"
                    ),
                }
            ],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        return str(response.choices[0].message.content or "").strip()


@dataclass(frozen=True)
class AnthropicProvider:
    async def summarize(
        self,
        file_path: str,
        file_content: str,
        model: str,
        api_key: str | None,
        base_url: str | None,
        max_tokens: int,
    ) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            base_url=base_url,
        )
        response = await client.messages.create(
            model=model or "claude-3-5-haiku-latest",
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Summarize this file in 2-4 concise lines. File: {file_path}\n\n"
                        f"{file_content[:8000]}"
                    ),
                }
            ],
        )
        block = response.content[0] if response.content else None
        return str(getattr(block, "text", "")).strip()


@dataclass(frozen=True)
class OllamaProvider:
    async def summarize(
        self,
        file_path: str,
        file_content: str,
        model: str,
        api_key: str | None,
        base_url: str | None,
        max_tokens: int,
    ) -> str:
        import httpx

        _ = api_key
        endpoint = (base_url or "http://localhost:11434").rstrip("/") + "/api/chat"
        payload = {
            "model": model or "llama3.1:8b",
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Summarize this file in 2-4 concise lines. File: {file_path}\n\n"
                        f"{file_content[:8000]}"
                    ),
                }
            ],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
        message = data.get("message", {}) if isinstance(data, dict) else {}
        return str(message.get("content", "")).strip()


_PROVIDER_REGISTRY: dict[str, LLMProvider] = {
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "ollama": OllamaProvider(),
}


def default_model_for(provider: str) -> str:
    if provider == "anthropic":
        return "claude-3-5-haiku-latest"
    if provider == "ollama":
        return "llama3.1:8b"
    return "gpt-4o-mini"


def llm_dependencies_available() -> bool:
    try:
        import anthropic  # noqa: F401
        import httpx  # noqa: F401
        import openai  # noqa: F401
    except Exception:
        return False
    return True


def _fallback_summary(file_path: str, file_content: str) -> str:
    non_empty = [line.strip() for line in file_content.splitlines() if line.strip()]
    preview = non_empty[0][:120] if non_empty else "empty file"
    return f"{file_path}: {preview}"


async def llm_summarize(
    file_path: str,
    file_content: str,
    provider: str,
    model: str,
    api_key: str | None,
    base_url: str | None,
    max_tokens: int,
) -> str:
    provider_impl = _PROVIDER_REGISTRY.get(provider)
    if provider_impl is None:
        return _fallback_summary(file_path, file_content)

    selected_model = model or default_model_for(provider)
    try:
        return await provider_impl.summarize(
            file_path=file_path,
            file_content=file_content,
            model=selected_model,
            api_key=api_key,
            base_url=base_url,
            max_tokens=max_tokens,
        )
    except Exception:
        return _fallback_summary(file_path, file_content)


def llm_summarize_sync(
    file_path: str,
    file_content: str,
    provider: str,
    model: str,
    api_key: str | None,
    base_url: str | None,
    max_tokens: int,
) -> str:
    return asyncio.run(
        llm_summarize(file_path, file_content, provider, model, api_key, base_url, max_tokens)
    )
