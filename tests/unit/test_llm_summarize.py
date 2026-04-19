"""Tests for async LLM summarization strategy layer."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

try:
    import openai
    import anthropic
    import httpx
    LLM_DEPS_AVAILABLE = True
except ImportError:
    LLM_DEPS_AVAILABLE = False

if LLM_DEPS_AVAILABLE:
    from codectx.llm import llm_summarize
else:
    llm_summarize = None  # type: ignore

from codectx.cli import app

runner = CliRunner()


@pytest.mark.skipif(not LLM_DEPS_AVAILABLE, reason="LLM dependencies not available")
def test_llm_summarize_openai() -> None:
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Summary text"))]
    )
    create = AsyncMock(return_value=completion)
    async_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with patch("openai.AsyncOpenAI", return_value=async_client) as async_openai:
        result = asyncio.run(
            llm_summarize(
                "foo.py",
                "def foo(): pass",
                "openai",
                "gpt-4o-mini",
                "sk-test",
                None,
                256,
            )
        )
    async_openai.assert_called_once()
    assert result == "Summary text"


@pytest.mark.skipif(not LLM_DEPS_AVAILABLE, reason="LLM dependencies not available")
def test_llm_summarize_fallback_on_error() -> None:
    with patch("openai.AsyncOpenAI", side_effect=Exception("network error")):
        result = asyncio.run(
            llm_summarize(
                "foo.py",
                "def foo(): pass",
                "openai",
                "gpt-4o-mini",
                None,
                None,
                256,
            )
        )

    assert isinstance(result, str)
    assert "foo.py" in result


def test_llm_flag_without_dependency_raises_usage_error(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "main.py").write_text("print('x')\n")
    monkeypatch.setattr("codectx.cli._LLM_AVAILABLE", False)

    result = runner.invoke(app, ["analyze", str(tmp_path), "--llm"])

    assert result.exit_code != 0
    assert "pip install codectx[llm]" in result.output


@pytest.mark.skipif(not LLM_DEPS_AVAILABLE, reason="LLM dependencies not available")
def test_llm_summarize_anthropic() -> None:
    response = SimpleNamespace(content=[SimpleNamespace(text="Anthropic summary")])
    create = AsyncMock(return_value=response)
    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    with patch("anthropic.AsyncAnthropic", return_value=client):
        result = asyncio.run(
            llm_summarize(
                "foo.py",
                "def foo(): pass",
                "anthropic",
                "claude-3-5-haiku-latest",
                "ak-test",
                None,
                256,
            )
        )

    assert result == "Anthropic summary"


@pytest.mark.skipif(not LLM_DEPS_AVAILABLE, reason="LLM dependencies not available")
def test_llm_summarize_ollama() -> None:
    response = MagicMock()
    response.json.return_value = {"message": {"content": "Ollama summary"}}
    response.raise_for_status.return_value = None

    post = AsyncMock(return_value=response)
    client = MagicMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    client.post = post

    with patch("httpx.AsyncClient", return_value=client) as async_client_cls:
        result = asyncio.run(
            llm_summarize(
                "foo.py",
                "def foo(): pass",
                "ollama",
                "llama3.1:8b",
                None,
                "http://localhost:11434",
                256,
            )
        )

    async_client_cls.assert_called_once()
    assert post.await_count == 1
    assert result == "Ollama summary"
