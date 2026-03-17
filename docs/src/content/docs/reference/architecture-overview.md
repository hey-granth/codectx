---
title: Architecture Overview
description: High-level overview of how codectx processes a codebase.
---

`codectx` is designed as a pipeline that sequentially processes a codebase to produce a deterministic output.

## Pipeline Walkthrough

1. **Discovery Phase**: The crawler scans the target directory, respecting `.gitignore` and `.codectx.yaml` exclude rules. It builds an initial flat file list.
2. **Parsing Phase**: Using Tree-sitter, it parses structural information from source files. This extracts functions, classes, and import declarations without executing the code.
3. **Graph Construction**: The parser identifies imports and builds a directional graph (the Dependency Graph). Circular dependencies are detected and resolved via topological sorting fallbacks.
4. **Ranking Engine**:
   - **Tier 1 (Core)**: Entry points, architecture docs, heavily depended-upon modules.
   - **Tier 2 (Logic)**: Standard implementation files.
   - **Tier 3 (Periphery)**: Utilities, tests, configuration scripts.
5. **Token Budgeting & Compression**: If a token limit is set, `codectx` selectively trims Tier 3, strips comments from Tier 2, and formats the output to fit securely within the requested budget.
6. **Formatting**: The internal models are rendered into the final Markdown structure optimized for LLM readability.
