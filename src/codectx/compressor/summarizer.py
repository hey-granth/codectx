"""LLM-based file summarization for Tier 3 compression.

This module is an optional dependency — all LLM imports are guarded.
Install with: pip install codectx[llm]
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from codectx.parser.base import ParseResult

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = (
    "Given this source file's symbols and imports, write one sentence describing "
    "what this module does. Be specific. No filler words.\n\n"
    "File: {path}\n"
    "Symbols: {symbols}\n"
    "Imports: {imports}\n"
)

# Track availability of LLM providers
_HAS_OPENAI = False
_HAS_ANTHROPIC = False

try:
    import openai  # noqa: F401

    _HAS_OPENAI = True
except ImportError:
    pass

try:
    import anthropic  # noqa: F401

    _HAS_ANTHROPIC = True
except ImportError:
    pass


def is_available() -> bool:
    """Check if any LLM provider is available."""
    return _HAS_OPENAI or _HAS_ANTHROPIC


def summarize_file(result: ParseResult, provider: str = "openai", model: str = "") -> str:
    """Return one-sentence summary of the file's purpose.

    Args:
        result: ParseResult for the file.
        provider: LLM provider ('openai' or 'anthropic').
        model: Model name (defaults to provider-specific default).

    Returns:
        One-sentence summary string.

    Raises:
        ImportError: If the required provider is not installed.
        RuntimeError: If the summarization call fails.
    """
    symbols = ", ".join(s.name for s in result.symbols) or "none"
    imports = ", ".join(result.imports[:10]) or "none"
    prompt = _PROMPT_TEMPLATE.format(
        path=result.path.name,
        symbols=symbols,
        imports=imports,
    )

    if provider == "openai":
        return _summarize_openai(prompt, model or "gpt-4o-mini")
    elif provider == "anthropic":
        return _summarize_anthropic(prompt, model or "claude-3-haiku-20240307")
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def summarize_files_batch(
    results: list[ParseResult],
    provider: str = "openai",
    model: str = "",
    max_workers: int = 4,
) -> dict[Path, str]:
    """Summarize multiple files concurrently.

    Args:
        results: List of ParseResult objects to summarize.
        provider: LLM provider name.
        model: Model name.
        max_workers: Max concurrent summarization threads.

    Returns:
        Dict mapping file path to summary string.
    """
    summaries: dict[Path, str] = {}

    def _do_one(pr: ParseResult) -> tuple[Path, str]:
        try:
            s = summarize_file(pr, provider, model)
            return (pr.path, s)
        except Exception as exc:
            logger.debug("LLM summarization failed for %s: %s", pr.path, exc)
            return (pr.path, "")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for path, summary in pool.map(_do_one, results):
            summaries[path] = summary

    return summaries


def _summarize_openai(prompt: str, model: str) -> str:
    """Call OpenAI API for summarization."""
    if not _HAS_OPENAI:
        raise ImportError("openai is not installed. Install with: pip install codectx[llm]")

    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.0,
    )
    return (response.choices[0].message.content or "").strip()


def _summarize_anthropic(prompt: str, model: str) -> str:
    """Call Anthropic API for summarization."""
    if not _HAS_ANTHROPIC:
        raise ImportError("anthropic is not installed. Install with: pip install codectx[llm]")

    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
