# Architecture

## Overview

codectx processes repositories through a structured analysis pipeline that ranks code by importance, compresses it intelligently, and emits a structured markdown document optimized for AI systems.

The pipeline consists of six stages: file discovery, parsing, graph construction, ranking, compression, and formatting.

## Pipeline

### Stage 1: Walker

**Purpose:** Discover repository files while respecting ignore rules.

The Walker recursively traverses the filesystem from the repository root and applies ignore rules in order:

1. `ALWAYS_IGNORE` — built-in patterns (`.git`, `__pycache__`, `.venv`, etc.)
2. `.gitignore` — Git standard ignore rules
3. `.ctxignore` — codectx-specific ignore rules

The tool uses `pathspec` with `gitwildmatch` semantics to ensure exact behavioral parity with Git's ignore processing.

**Output:** `List[Path]` of files to analyze.

### Stage 2: Parser

**Purpose:** Extract imports, symbols, and metadata from source files.

The Parser processes files in parallel using `ProcessPoolExecutor` (CPU-bound) and `ThreadPoolExecutor` (I/O-bound). For each file:

1. Detect language from file extension
2. Parse AST using tree-sitter
3. Extract:
   - Import statements (list of import strings)
   - Top-level symbols (functions, classes, methods)
   - Docstrings per symbol
   - Code structure metadata

Tree-sitter provides a unified interface across six+ languages: Python, TypeScript, JavaScript, Go, Rust, Java, C, C++, and Ruby.

**Output:** `Dict[Path, ParseResult]` where each `ParseResult` contains imports, symbols, and source text.

### Stage 3: Dependency Graph

**Purpose:** Build a directed graph representing module relationships.

The Graph Builder processes parse results to construct a `rustworkx.DiGraph`:

1. For each import statement, resolve the import string to a file path using per-language import resolvers
2. Create nodes for files and edges for import relationships
3. Compute graph metrics:
   - **Fan-in** — in-degree per node (how many files import this module)
   - **Fan-out** — out-degree per node (how many modules this file imports)
   - **Strongly connected components** — detect cyclic dependencies
4. Build symbol cross-reference edges (`symbol_ref`) from parser symbol usage data

The graph builder now exposes symbol references through `get_symbol_references()` so downstream formatters can emit cross-file symbol usage in structured output.

The graph enables ranking algorithms to identify important modules based on structural position.

**Output:** `rustworkx.DiGraph` with computed metrics.

### Stage 4: Ranker

**Purpose:** Score files by importance using multiple signals.

The Ranker computes a composite importance score for each file:

```
score = (0.40 × git_frequency)
      + (0.40 × fan_in)
      + (0.10 × recency)
      + (0.10 × entry_proximity)
```

**Git Frequency (0.40):** Commit count touching the file. Frequently-modified files are typically more important.

**Fan-in (0.40):** Inverse-normalized in-degree. Files imported by many other modules are critical interfaces.

**Recency (0.10):** Days since last modification. Recently active files are prioritized.

**Entry Proximity (0.10):** Graph distance from identified entry points. Files close to main execution paths rank higher.

Scores are normalized to `[0.0, 1.0]` range for uniform compression tier assignment. Semantic searches (`--query`) inject a 5th signal at 20% weight and rescale the other four to 80%.

**Output:** `Dict[Path, float]` mapping file paths to scores.

### Stage 5: Compressor

**Purpose:** Fit code content within a token budget.

The Compressor assigns content tiers based on scored percentiles:

- **Tier 1** (Top 15%) — AST-driven structured summaries or full source code for true entry points
- **Tier 2** (Next 30%) — Function signatures and docstrings only
- **Tier 3** (Remaining) — One-line summaries

A Summarizer step (`--llm` extras) runs specifically evaluating `Tier 3` code mapping out detailed functions implicitly before output mapping.

Files are emitted in order: Tier 1 by score descending, then Tier 2, then Tier 3.

If total token count exceeds the budget:

1. Drop all Tier 3 files
2. Truncate Tier 2 content (keep only signatures, remove docstrings)
3. Truncate Tier 1 content (reduce line count progressively)
4. If still over budget, drop lowest-scored Tier 1 files

This is a hard constraint. The tool does not emit context that exceeds the token limit.

**Output:** `Dict[Path, CompressedContent]` and usage statistics.

### Stage 6: Formatter

**Purpose:** Emit structured markdown optimized for AI agents.

The Formatter writes sections in fixed order:

1. **ARCHITECTURE** — High-level project structure derived from files
2. **ENTRY_POINTS** — Main files and public interfaces with full source
3. **SYMBOL_INDEX** — Identifies references and mappings across the codebase
4. **IMPORTANT_CALL_PATHS** — Tracks deep operational flows sequentially
5. **CORE_MODULES** — High-scoring modules with structured logic constraints
6. **SUPPORTING_MODULES** — Mid-scoring modules with signatures and docstrings
7. **DEPENDENCY_GRAPH** — Mermaid diagram of module relationships
8. **RANKED_FILES** — Sorted layout tracking cost algorithms
9. **PERIPHERY** — Low-scoring files with one-line summaries

Each section is preceded by a Markdown heading and terminated with metadata (token count, file count).

The formatter supports two output modes:

- `markdown` (default): writes human-readable context sections to `CONTEXT.md`
- `json`: writes a machine-readable payload with top-level schema fields such as `version`, `root`, `budget_tokens`, `totals`, `files`, and `sections`

**Output:** Markdown string or JSON payload suitable for writing to disk.

## Cache Subsystem

The cache subsystem is split into three concerns:

- `cache/paths.py` resolves repo-scoped cache paths under `~/.cache/codectx` or `$XDG_CACHE_HOME/codectx`
- `cache/manifest.py` stores run-level manifest metadata (options + file hashes) used for up-to-date short-circuit checks
- Semantic embedding cache persists vectors in LanceDB and evicts stale rows for removed paths

Embedding cache invalidation is content-hash based, and stale-embedding eviction runs after successful embedding updates.

## Data Flow Diagram

```
File System
    │
    ├─→ [Walker] 
    │   ├ Respects .gitignore
    │   ├ Respects .ctxignore
    │   └ Output: List[Path]
    │
    ├─→ [Parser] (Parallel)
    │   ├ Per-language extraction
    │   ├ tree-sitter AST processing
    │   └ Output: Dict[Path, ParseResult]
    │
    ├─→ [Graph Builder]
    │   ├ Resolve imports
    │   ├ Construct DiGraph
    │   └ Output: rustworkx.DiGraph
    │
    ├─→ [Git Metadata] (Parallel)
    │   ├ Commit frequency per file
    │   ├ Recency (last modification)
    │   └ Output: Dict[Path, GitMeta]
    │
    ├─→ [Ranker]
    │   ├ Composite scoring
    │   ├ Normalize to [0.0, 1.0]
    │   └ Output: Dict[Path, float]
    │
    ├─→ [Compressor]
    │   ├ Tier assignment
    │   ├ Token budget enforcement
    │   ├ [Optional: AI Summarizer hooks]
    │   └ Output: Dict[Path, CompressedContent]
    │
    └─→ [Formatter]
        ├ Section organization
        ├ Markdown generation
        └ Output: CONTEXT.md
```

## Caching

The tool caches expensive computations:

**Cache key:** `(file_path, file_hash, git_commit_sha)`

**Cached items:**
- Parsed AST and extracted symbols per file
- Git metadata (frequency, recency)

**Cache location:** `.codectx_cache/` at repository root (gitignored)

**Invalidation:** Cache entries are invalidated when file content changes or HEAD commit changes.

This enables fast incremental updates in watch mode.

## Incremental Mode

When running `codectx watch .`, the tool:

1. Monitors filesystem with `watchfiles`
2. On file change:
   - Reparse only affected files
   - Rebuild graph for changed nodes and dependents
   - Re-rank affected subgraph
   - Recompress to budget
   - Re-emit output

This is significantly faster than full analysis on every change.

## Token Budget Enforcement

Token counting uses `tiktoken`, which accurately reflects OpenAI and Anthropic model tokenization.

Budget enforcement is hard: the tool does not emit context exceeding the specified limit.

Consumption order:

1. Fixed overhead (section headers, metadata) — typically 500–1000 tokens
2. Tier 1 files by score descending (AST Summaries / Full source)
3. Tier 2 files by score descending (signatures only)
4. Tier 3 files by score descending (one-line summaries)

Files omitted due to budget are logged with a note in the output.

## Language Support

The Parser uses tree-sitter for universal AST extraction. Each language requires:

1. **tree-sitter grammar** — provided by `tree-sitter-LANGUAGE` package
2. **Import resolver** — per-language logic to resolve import strings to file paths

Currently supported:

- **Python**
- **TypeScript/JavaScript**
- **Go**
- **Rust**
- **Java**
- **C/C++**
- **Ruby**

Adding a language requires implementing a resolver in `src/codectx/graph/resolver.py` and adding the grammar dependency to `pyproject.toml`.

## Configuration

Configuration is applied in this precedence order:

1. **CLI flags** (highest priority)
2. **`.codectx.toml`** in repository root
3. **Built-in defaults** (lowest priority)

Example `.codectx.toml`:

```toml
[codectx]
token_budget = 120000
output_file = "CONTEXT.md"
extra_ignore = ["**/generated/**", "*.draft.py"]
```
