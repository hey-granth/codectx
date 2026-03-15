"""Tiered compression — assigns tiers and enforces token budget."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from codectx.compressor.budget import TokenBudget, count_tokens
from codectx.config.defaults import (
    ENTRYPOINT_FILENAMES,
    MAX_ENTRYPOINT_LINES,
)
from codectx.parser.base import ParseResult


@dataclass(frozen=True)
class CompressedFile:
    """A file compressed to its assigned tier."""

    path: Path
    tier: int  # 1, 2, or 3
    score: float
    content: str
    token_count: int
    language: str


_NON_SOURCE_DIRS: frozenset[str] = frozenset(
    {
        "tests",
        "test",
        "docs",
        "doc",
        "examples",
        "example",
        "benchmarks",
        "benchmark",
        "scripts",
        "script",
    }
)


def _is_non_source(path: Path, root: Path) -> bool:
    """Return True if the file lives under a non-source directory."""
    try:
        parts = set(path.relative_to(root).parts)
    except ValueError:
        return False
    return bool(parts.intersection(_NON_SOURCE_DIRS))


def assign_tiers(
    scores: dict[Path, float],
) -> dict[Path, int]:
    """Assign tiers by score percentile.

    Top 15% -> Tier 1, next 30% -> Tier 2, rest -> Tier 3.
    Ties at the threshold are promoted into the higher tier.
    """
    if not scores:
        return {}

    sorted_scores = sorted(scores.values(), reverse=True)
    n = len(sorted_scores)

    tier1_cutoff_idx = max(1, int(n * 0.15))
    tier2_cutoff_idx = max(2, int(n * 0.45))

    tier1_threshold = sorted_scores[tier1_cutoff_idx - 1]
    tier2_threshold = sorted_scores[min(tier2_cutoff_idx - 1, n - 1)]

    tiers: dict[Path, int] = {}
    for path, score in scores.items():
        if score >= tier1_threshold:
            tiers[path] = 1
        elif score >= tier2_threshold:
            tiers[path] = 2
        else:
            tiers[path] = 3
    return tiers


def compress_files(
    parse_results: dict[Path, ParseResult],
    scores: dict[Path, float],
    budget: TokenBudget,
    root: Path,
    llm_enabled: bool = False,
    llm_provider: str = "openai",
    llm_model: str = "",
) -> list[CompressedFile]:
    """Compress files into tiered content within the token budget.

    Budget consumption order:
      1. Tier 1 files (full source), by score descending
      2. Tier 2 files (signatures + docstrings), by score descending
      3. Tier 3 files (one-line summary), by score descending

    Overflow policy: drop Tier 3 → truncate Tier 2 → truncate Tier 1.
    """
    tiers = assign_tiers(scores)

    # Force non-source files to Tier 3 regardless of score
    for path in list(tiers.keys()):
        if _is_non_source(path, root):
            tiers[path] = 3

    # Group and sort files by score, then path
    def sort_key(p: Path) -> tuple[float, str]:
        return (-scores.get(p, 0.0), p.as_posix())

    sorted_paths = sorted(parse_results.keys(), key=sort_key)

    tier1: list[Path] = []
    tier2: list[Path] = []
    tier3: list[Path] = []

    for path in sorted_paths:
        tier = tiers.get(path, 3)
        if tier == 1:
            tier1.append(path)
        elif tier == 2:
            tier2.append(path)
        else:
            tier3.append(path)

    result: list[CompressedFile] = []

    # Process Tier 1 — full source
    for path in tier1:
        pr = parse_results[path]
        content = _tier1_content(pr, path, root)
        tokens = count_tokens(content)

        if budget.remaining >= tokens:
            budget.consume(tokens)
            result.append(
                CompressedFile(
                    path=path,
                    tier=1,
                    score=scores.get(path, 0.0),
                    content=content,
                    token_count=tokens,
                    language=pr.language,
                )
            )
        else:
            # Truncate Tier 1 to fit
            truncated = budget.consume_partial(content)
            if truncated:
                result.append(
                    CompressedFile(
                        path=path,
                        tier=1,
                        score=scores.get(path, 0.0),
                        content=truncated,
                        token_count=count_tokens(truncated),
                        language=pr.language,
                    )
                )

    # Process Tier 2 — signatures + docstrings
    for path in tier2:
        if budget.is_exhausted:
            break
        pr = parse_results[path]
        content = _tier2_content(pr, path, root)
        tokens = count_tokens(content)

        if budget.remaining >= tokens:
            budget.consume(tokens)
            result.append(
                CompressedFile(
                    path=path,
                    tier=2,
                    score=scores.get(path, 0.0),
                    content=content,
                    token_count=tokens,
                    language=pr.language,
                )
            )
        else:
            truncated = budget.consume_partial(content)
            if truncated:
                result.append(
                    CompressedFile(
                        path=path,
                        tier=2,
                        score=scores.get(path, 0.0),
                        content=truncated,
                        token_count=count_tokens(truncated),
                        language=pr.language,
                    )
                )

    # Process Tier 3 — one-line summaries (dropped first on overflow)
    # Pre-compute LLM summaries if enabled
    llm_summaries: dict[Path, str] = {}
    if llm_enabled and tier3:
        try:
            from codectx.compressor.summarizer import is_available, summarize_files_batch

            if is_available():
                tier3_results = [parse_results[p] for p in tier3]
                llm_summaries = summarize_files_batch(tier3_results, llm_provider, llm_model)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).debug("LLM summarization failed, using heuristic: %s", exc)

    for path in tier3:
        if budget.is_exhausted:
            break
        pr = parse_results[path]

        # Use LLM summary if available, otherwise heuristic
        if path in llm_summaries and llm_summaries[path]:
            rel = path.relative_to(root).as_posix()
            content = f"- `{rel}` — {llm_summaries[path]}\n"
        else:
            content = _tier3_content(pr, path, root)

        tokens = count_tokens(content)

        if budget.remaining >= tokens:
            budget.consume(tokens)
            result.append(
                CompressedFile(
                    path=path,
                    tier=3,
                    score=scores.get(path, 0.0),
                    content=content,
                    token_count=tokens,
                    language=pr.language,
                )
            )
        # Tier 3 files are simply dropped if they don't fit

    # Sort result for deterministic output: tier → score desc → path
    result.sort(key=lambda cf: (cf.tier, -cf.score, cf.path.as_posix()))

    return result


# ---------------------------------------------------------------------------
# Content generators per tier
# ---------------------------------------------------------------------------


def _tier1_content(pr: ParseResult, path: Path, root: Path) -> str:
    """Tier 1: full source with metadata header."""
    rel = path.relative_to(root).as_posix()
    lang = pr.language if pr.language != "unknown" else ""
    header = f"### `{rel}`\n"

    source = pr.raw_source
    if path.name in ENTRYPOINT_FILENAMES:
        lines = source.split("\n")
        if len(lines) > MAX_ENTRYPOINT_LINES:
            source = "\n".join(lines[:MAX_ENTRYPOINT_LINES])
            source += f"\n\n... (truncated: entry point exceeds {MAX_ENTRYPOINT_LINES} lines)"

    return f"{header}\n```{lang}\n{source}\n```\n"


def _tier2_content(pr: ParseResult, path: Path, root: Path) -> str:
    """Tier 2: function/class signatures + docstrings."""
    rel = path.relative_to(root).as_posix()
    lines: list[str] = [f"### `{rel}`\n"]

    if pr.docstrings:
        lines.append(f"> {pr.docstrings[0]}\n")

    if pr.symbols:
        lang = pr.language if pr.language != "unknown" else ""
        lines.append(f"```{lang}")
        for sym in pr.symbols:
            lines.append(sym.signature)
            if sym.docstring:
                lines.append(f'    """{sym.docstring}"""')
            lines.append("")
        lines.append("```\n")
    else:
        lines.append(f"*{pr.line_count} lines, {len(pr.imports)} imports*\n")

    return "\n".join(lines)


def _tier3_content(pr: ParseResult, path: Path, root: Path) -> str:
    """Tier 3: one-line summary."""
    rel = path.relative_to(root).as_posix()
    summary = _one_line_summary(pr)
    return f"- `{rel}` — {summary}\n"


def _one_line_summary(pr: ParseResult) -> str:
    """Generate a one-line summary from parse result."""
    parts: list[str] = []

    if pr.docstrings:
        # Use first docstring, truncated
        doc = pr.docstrings[0].split("\n")[0][:80]
        return doc

    if pr.symbols:
        sym_names = [s.name for s in pr.symbols[:5]]
        kind_counts: dict[str, int] = {}
        for s in pr.symbols:
            kind_counts[s.kind] = kind_counts.get(s.kind, 0) + 1
        for kind, count in sorted(kind_counts.items()):
            parts.append(f"{count} {kind}{'s' if count > 1 else ''}")

    if pr.imports:
        parts.append(f"{len(pr.imports)} imports")

    parts.append(f"{pr.line_count} lines")

    return ", ".join(parts)
