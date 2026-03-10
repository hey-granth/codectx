# codectx

## What this is
Codebase context compiler for AI agents. Parses a repo, ranks files by semantic importance,
compresses to a token budget, and outputs structured markdown consumable by any LLM agent.

Not a file concatenator. A codebase compiler whose target architecture is an LLM attention mechanism.

## Stack
- Python 3.10+
- tree-sitter + tree-sitter-languages — AST parsing, language agnostic
- rustworkx — dependency graph (drop-in networkx API, Rust core)
- pygit2 — git metadata (log frequency, recency, blame)
- tiktoken — token counting
- typer + rich — CLI
- pathspec — .gitignore / .ctxignore pattern matching

## Project structure
```
src/codectx/
├── cli.py              # typer entrypoint, wires full pipeline
├── walker.py           # file discovery, applies ignore specs
├── ignore.py           # .gitignore + .ctxignore + ALWAYS_IGNORE handling
├── safety.py           # sensitive file detection + user confirmation
├── parser/
│   ├── base.py         # ParseResult dataclass, abstract interface
│   ├── treesitter.py   # tree-sitter AST extraction per language
│   └── languages.py    # extension → language mapping
├── ranker/
│   ├── scorer.py       # composite score: git_freq + fan_in + recency
│   └── git_meta.py     # pygit2 wrappers for log/blame/recency
├── graph/
│   ├── builder.py      # rustworkx graph construction from import lists
│   └── resolver.py     # per-language import → file path resolution
├── compressor/
│   ├── tiered.py       # assign tier per file against token budget
│   └── budget.py       # token counting, budget enforcement
├── output/
│   ├── formatter.py    # structured markdown emitter
│   └── sections.py     # section constants and ordering
└── config/
    ├── loader.py       # .contextcraft.toml loader
    └── defaults.py     # default config values
```

## Pipeline
```
Codebase
  → walker       (discover files, apply ignore specs)
  → parser       (AST per file → imports + symbols)
  → graph        (dependency graph from imports)
  → ranker       (score files: git_freq + fan_in + recency)
  → compressor   (assign tier against token budget)
  → formatter    (emit structured markdown)
  → output file
```

## Tier definitions
| Tier | Score range | Output |
|------|-------------|--------|
| 1    | > 0.7       | Full source |
| 2    | 0.3 – 0.7   | Signatures + docstrings only |
| 3    | < 0.3       | Module name + one-line summary |

Token budget enforcement: Tier 3 dropped first, then Tier 2 truncated, then Tier 1 truncated.

## Output structure
```markdown
[ARCHITECTURE]      ← from .contextcraft.toml or auto-generated
[DEPENDENCY GRAPH]  ← mermaid diagram from graph builder
[ENTRY POINTS]      ← Tier 1 files, full source
[CORE MODULES]      ← Tier 2 files, compressed
[PERIPHERY]         ← Tier 3 files, signatures only
[RECENT CHANGES]    ← git diff if --since provided
```

## Conventions
- Type hints on every function signature, no exceptions
- Dataclasses for structured return types, never raw dicts
- pathlib.Path everywhere, never str for file paths
- Errors raised explicitly with context, never swallowed silently
- No class where a module-level function works
- ProcessPoolExecutor for CPU-bound work (parsing), ThreadPoolExecutor for I/O
- All constants in config/defaults.py, never hardcoded inline

## Current focus
See PLAN.md

## Settled decisions
See DECISIONS.md — do not re-litigate choices documented there
