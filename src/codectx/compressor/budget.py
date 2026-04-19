"""Token counting and budget tracking via tiktoken."""

from __future__ import annotations

from typing import cast

import tiktoken

from codectx.config.defaults import DEFAULT_TOKEN_BUDGET, TIKTOKEN_ENCODING

# Lazily initialized encoder
_encoder: tiktoken.Encoding | None = None


def _get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding(TIKTOKEN_ENCODING)
    return _encoder


def count_tokens(text: str) -> int:
    """Count the number of tokens in *text*."""
    return len(_get_encoder().encode(text, disallowed_special=()))


class TokenBudget:
    """Tracks remaining token budget during context assembly."""

    def __init__(self, total: int = DEFAULT_TOKEN_BUDGET) -> None:
        self.total = total
        self.used = 0

    @property
    def remaining(self) -> int:
        return max(self.total - self.used, 0)

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 0

    def consume(self, tokens: int) -> bool:
        """Consume tokens from the budget. Returns True if successful."""
        if tokens <= self.remaining:
            self.used += tokens
            return True
        return False

    def consume_partial(self, text: str, max_tokens: int | None = None) -> str:
        """Consume as much of *text* as fits within the budget.

        Returns the (possibly truncated) text that was consumed.
        """
        limit = min(max_tokens, self.remaining) if max_tokens else self.remaining

        if limit <= 0:
            return ""

        enc = _get_encoder()
        tokens = enc.encode(text, disallowed_special=())

        if len(tokens) <= limit:
            self.used += len(tokens)
            return text

        # Truncate to fit
        truncated_tokens = tokens[:limit]
        self.used += len(truncated_tokens)
        truncated = cast(str, enc.decode(truncated_tokens))
        return truncated + "\n... [truncated to fit token budget]"
