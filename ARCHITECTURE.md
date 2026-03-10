# Architecture

## Problem
AI agents receive poor codebase context because existing tools (repomix, etc.) are file
concatenators. They dump files in filesystem order with no ranking, no compression, and no
semantic structure. Agent output quality is bounded by signal-to-noise ratio in the context window.

## Solution
Treat context generation as compilation. Parse the codebase into a dependency graph, rank files
by importance signals, compress to a token budget, and emit structured output that orients an
agent immediately.

## Pipeline

```
Codebase
  │
  ▼
Walker
  - Recursive file discovery from root
  - Applies ALWAYS_IGNORE, .gitignore, .ctxignore in order
  - Warns and confirms on sensitive file detection
  - Returns: List[Path]
  │
  ▼
Parser (parallel, ProcessPoolExecutor)
  - Detects language from file extension
  - Extracts via tree-sitter AST:
      - Import statements → List[str]
      - Top-level symbols (functions, classes) → List[Symbol]
      - Docstrings per symbol
  - Returns: Dict[Path, ParseResult]
  │
  ▼
Graph Builder
  - Resolves import strings → file paths (per-language resolver)
  - Constructs rustworkx DiGraph: nodes=files, edges=imports
  - Computes fan-in (in-degree) per node
  - Returns: DepGraph
  │
  ▼
Ranker
  - Scores each file 0.0–1.0 using weighted composite:
      git_frequency  : 0.35  (commit count touching file)
      fan_in         : 0.35  (how many files import this)
      recency        : 0.20  (days since last modification)
      entry_proximity: 0.10  (graph distance from entry points)
  - Returns: Dict[Path, float]
  │
  ▼
Compressor
  - Enforces token budget (from config or CLI flag)
  - Assigns tier per file by score:
      Tier 1 (score > 0.7): full source
      Tier 2 (score 0.3–0.7): signatures + docstrings
      Tier 3 (score < 0.3): one-line summary
  - If over budget: drop Tier 3 → truncate Tier 2 → truncate Tier 1
  - Returns: Dict[Path, CompressedFile]
  │
  ▼
Formatter
  - Emits structured markdown with fixed section order
  - Sections: ARCHITECTURE, DEPENDENCY_GRAPH, ENTRY_POINTS,
              CORE_MODULES, PERIPHERY, RECENT_CHANGES
  - Returns: str
  │
  ▼
Output file (default: context.md)
```

## Parallelism model
- File parsing: ProcessPoolExecutor (CPU-bound, tree-sitter C extension)
- File I/O: ThreadPoolExecutor (I/O-bound, reading source files)
- Graph construction: single-threaded (fast, rustworkx handles it)
- Ranking: single-threaded (fast after git metadata collected)

## Caching
- Cache key: (file_path, file_hash, git_commit_sha)
- Cache location: .codectx_cache/ at project root (gitignored)
- Cached: ParseResult per file, git metadata per file
- Invalidated: on file content change or new commit

## Incremental mode (--watch)
- watchfiles monitors project root
- On change: reparse affected files only
- Rebuild graph for changed nodes and their dependents
- Re-rank affected subgraph
- Re-emit output

## Token budget enforcement
Hard cap. Not a suggestion. Budget is consumed in this order:
1. ARCHITECTURE section (fixed, small)
2. DEPENDENCY_GRAPH section (fixed, small)
3. Tier 1 files by rank score descending
4. Tier 2 files by rank score descending
5. Tier 3 files by rank score descending

Files that don't fit are omitted with a note in the output.

## Language support
Pluggable resolver interface. Initial support:
- Python (.py)
- TypeScript (.ts, .tsx)
- JavaScript (.js, .jsx)
- Go (.go)
- Rust (.rs)
- Java (.java)

Adding a language requires: tree-sitter grammar (via tree-sitter-languages) + import resolver.

## Config precedence
CLI flags > .contextcraft.toml > defaults
