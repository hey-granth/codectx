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
  -t, --tokens INTEGER            Token budget (default: 120000).
  -o, --output PATH               Output file path (default: CONTEXT.md).
  --since TEXT                    Include recent changes since this date (e.g. '7 days ago').
  -v, --verbose                   Enable verbose logging.
  --no-git                        Skip git metadata collection.
  -q, --query TEXT                Semantic query to rank files by relevance (requires codectx[semantic]).
  --task TEXT                     Task profile for context generation (debug, feature, architecture, refactor, default). (default: default)
  --layers                        Generate layered context output.
  --extra-root PATH               Additional root directories for multi-root analysis.
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
  -t, --tokens INTEGER
  -o, --output PATH
  -v, --verbose
  --no-git
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

Manage the internal parse and embedding cache.

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
