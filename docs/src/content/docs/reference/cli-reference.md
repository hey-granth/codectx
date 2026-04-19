---
title: CLI Reference
description: Complete reference for the codectx Command Line Interface.
---

This page provides a complete reference for all `codectx` commands and their flags.

## `analyze`

The primary command to compile a repository into a Context specification.

```text
Usage: codectx analyze [OPTIONS] [ROOT]

Arguments:
  [ROOT]  Repository root directory to analyze. (default: .)

Options:
  --budget, --tokens, -t INTEGER  Token budget for context output (default: 120000).
  -o, --output PATH               Output file path (default: CONTEXT.md).
  --exclude TEXT                  Glob patterns to exclude (repeatable).
  --since TEXT                    Include recent changes since this date (e.g. '7 days ago').
  -v, --verbose                   Enable verbose logging.
  --no-git                        Skip git metadata collection.
  -q, --query TEXT                Semantic query to rank files by relevance (requires codectx[semantic]).
  --task TEXT                     Task profile for context generation (debug, feature, architecture, default). (default: default)
  --layers                        Generate layered context output.
  --extra-root PATH               Additional root directories for multi-root analysis.
  --format TEXT                   Output format: markdown or json (default: markdown).
  --llm / --no-llm                Enable LLM-powered file summaries (default: no-llm).
  --llm-provider TEXT             LLM provider: openai, anthropic, or ollama (default: openai).
  --llm-model TEXT                Model string for the chosen provider. Uses provider default if empty.
  --llm-api-key TEXT              API key override. Falls back to OPENAI_API_KEY or ANTHROPIC_API_KEY.
  --llm-base-url TEXT             Override base URL, e.g. for Ollama or compatible endpoints.
  --llm-max-tokens INTEGER        Max tokens per LLM summary (default: 256).
  --force                         Bypass cache check and regenerate unconditionally.
  --help                          Show this message and exit.
```

## `benchmark`

Run analysis with detailed timing and stats.

```text
Usage: codectx benchmark [OPTIONS] [ROOT]

Arguments:
  [ROOT]  Repository root directory. (default: .)

Options:
  -t, --tokens INTEGER
  -v, --verbose
  --no-git
  --help                Show this message and exit.
```

## `watch`

Watch for file changes and regenerate CONTEXT.md automatically.

```text
Usage: codectx watch [OPTIONS] [ROOT]

Arguments:
  [ROOT]  Repository root directory. (default: .)

Options:
  --budget, --tokens, -t INTEGER  Token budget forwarded to analyze on each rebuild.
  -o, --output PATH               Output file path forwarded to analyze on each rebuild.
  --format TEXT                   Output format forwarded to analyze on each rebuild.
  --exclude TEXT                  Glob patterns to exclude (repeatable).
  --debounce FLOAT                Seconds to wait after last change before re-analyzing (default: 3.0).
  -v, --verbose                   Enable verbose logging.
  --no-git                        Skip git metadata collection.
  --help                Show this message and exit.
```

## `search`

Search the codebase semantically. Requires the `[semantic]` extra.

```text
Usage: codectx search [OPTIONS] QUERY

Arguments:
  QUERY  Semantic search query.  [required]

Options:
  -r, --root PATH       Repository root directory. (default: .)
  -l, --limit INTEGER   Number of results to return. (default: 10)
  -v, --verbose         Enable verbose logging.
  --help                Show this message and exit.
```

## `cache`

Manage the codectx cache for a repository.

### `cache export`

Export the cache as a tar.gz archive for CI sharing.

```text
Usage: codectx cache export [OPTIONS] [ROOT]

Arguments:
  [ROOT]  Repository root directory. (default: .)

Options:
  -o, --output PATH  Output archive path. (default: .codectx_cache.tar.gz)
  --help             Show this message and exit.
```

### `cache import`

Import a cache archive for CI sharing.

```text
Usage: codectx cache import [OPTIONS] [ROOT]

Arguments:
  [ROOT]  Repository root directory. (default: .)

Options:
  -i, --input PATH  Input archive path. (default: .codectx_cache.tar.gz)
  --help            Show this message and exit.
```

### `cache clear`

Clear the codectx cache for this repository.

```text
Usage: codectx cache clear [OPTIONS] [ROOT]

Arguments:
  [ROOT]  Repository root whose cache to delete (default: .)

Options:
  --force, --all  Skip confirmation prompt.
  --help          Show this message and exit.
```

### `cache info`

Show information about the codectx cache for this repository.

```text
Usage: codectx cache info [OPTIONS] [ROOT]

Arguments:
  [ROOT]  Repository root to inspect (default: .)

Options:
  --help  Show this message and exit.
```

