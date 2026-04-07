---
title: Configuration
description: Configuring codectx via TOML and CLI flags.
---

While `codectx` works out of the box with zero configuration, you can fine-tune its behavior.

## The `.codectx.toml` file

Place a `.codectx.toml` file in the root of your repository (or add a `[tool.codectx]` section to `pyproject.toml`) to persist configuration options.

```toml
# .codectx.toml

# Explicit file patterns to ignore
extra_ignore = [
    "**/generated/**",
    "*.draft.py"
]

# The token constraint limit for generated Context output
token_budget = 100000

# Destination relative to cwd
output_file = "CONTEXT.md"

# Generate multilayer output files alongside the main file
layers = false

# Enable/disable git tracking algorithms
no_git = false

# Use language model embeddings or skip over heuristics based
llm_enabled = false
llm_provider = "openai"
llm_model = ""

# Track the project since specific interval string
since = "7 days ago"
```

## CLI Overrides

Any value in the `.codectx.toml` file can be overridden via the CLI during generation:

```bash
codectx analyze . --tokens 50000 --no-git
```

## Ignoring Files

By default, `codectx` ignores binaries, cache, and items within your standard `.gitignore` and an optional `.ctxignore` file. You can augment this using `extra_ignore` arrays within `.codectx.toml` or the `pyproject.toml` tool key.
