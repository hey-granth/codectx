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
   - **Tier 1 (Core)**: Entry points and heavily depended-upon modules.
   - **Tier 2 (Logic)**: Standard implementation files.
   - **Tier 3 (Periphery)**: Utilities, tests, configuration scripts.
5. **Token Budgeting & Compression**: If a token limit is set, `codectx` selectively compresses Tier 2 to strictly interfaces/signatures, trims Tier 3 to one-liners, and transforms Tier 1 files (save for true entry points) into highly descriptive AST structural summaries.
6. **Summarizer Extension**: Before executing final formatting, if the `--llm` extra flag properties have been enabled, Tier 3 components utilize an AI summarization hook for explicit purpose mappings.
7. **Formatting**: The internal models are incrementally rendered into the final Markdown structure optimized for LLM readability.

## Formatted Output Sections

The final documentation generated produces sections exactly mapped sequentially for deterministic consumption. Here are the core structural mappings `codectx` derives within the files:
- `ARCHITECTURE`: Derived manually from source instructions (`ARCHITECTURE.md`).
- `ENTRY_POINTS`: Source outputs explicitly identifying core routing operations.
- `SYMBOL_INDEX`: High level references and their localized mapping details.
- `IMPORTANT_CALL_PATHS`: Topologically parsed chains determining exact dependency flow between symbols.
- `CORE_MODULES`: Structured outputs referencing the `Tier 1` implementation bodies.
- `SUPPORTING_MODULES`: Strictly defined `Tier 2` interface summaries spanning generic files.
- `DEPENDENCY_GRAPH`: ASCII Rendered mappings establishing connection flow throughout implementations.
- `RANKED_FILES`: Sorted layout confirming the resulting file-system evaluations.
- `PERIPHERY`: Evaluated `Tier 3` elements compressed significantly or derived via heuristics/summaries.
