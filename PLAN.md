# codectx — Development Plan

## v0.3.0 — ✅ Released 2026-04-19

- [x] Persistent semantic embedding cache with hash invalidation
- [x] Debounced watch mode (`--debounce`) with relevant-source filtering
- [x] JSON output support via `--format json`
- [x] LLM summarization CLI options (`--llm`, provider/model/base-url)
- [x] Symbol cross-reference edges and exported symbol reference data
- [x] Constants extraction coverage in structured summaries
- [x] Config-file demotion behavior for ranking/output
- [x] Mypy workflow updated to `mypy src/codectx --strict`

## v0.4.0 — Planned

- Incremental watch pipeline improvements
- Additional language/resolver depth
- Documentation and schema hardening for programmatic consumers

## What ships today (v0.1.3 / v0.2.0)

### Pipeline

- Repository scanning with `.gitignore` and `.ctxignore` support
- Parallel AST parsing via tree-sitter across 9 languages
- Dependency graph construction using rustworkx
- Composite file scoring — fan-in centrality, git commit frequency, entry-point proximity, recency
- Percentile-based tier assignment (top 15% → structured summary, next 30% → signatures, rest → one-liners)
- Budget-driven inclusion — no static file caps, budget exhaustion is the only stopping condition
- AST-driven structured summaries for Tier 1 non-entry-point files
- Full source for entry point files (cli.py, main.py, app.py, etc.)
- Hard token budget enforcement with partial truncation on overflow
- Deterministic output — identical repositories produce byte-identical CONTEXT.md

### Language support

Python, TypeScript, JavaScript, Go, Rust, Java, C, C++, Ruby.

### CLI

- `codectx analyze .` — generate context
- `codectx watch .` — regenerate on file changes
- `codectx search <query>` — semantic file search (requires `[semantic]` extra)
- `--tokens` — custom token budget
- `--output` — custom output path
- `--since` — include recent git changes section
- `--task` — ranking profile: `default`, `debug`, `feature`, `architecture`, `refactor`
- `--query` — semantic similarity ranking via sentence-transformers + lancedb
- `--layers` — emit separate REPO_MAP.md and CORE_CONTEXT.md
- `--no-git` — skip git metadata, use filesystem fallback
- `--verbose` — debug logging

### Output sections

ARCHITECTURE, ENTRY_POINTS, SYMBOL_INDEX, IMPORTANT_CALL_PATHS, CORE_MODULES, SUPPORTING_MODULES, DEPENDENCY_GRAPH, RANKED_FILES, PERIPHERY

### Infrastructure

- JSON-based parse cache with SHA-256 file hashing
- Cache export/import for CI sharing
- Symlink-safe walker
- Proper `.venv` and non-source directory exclusion
- Safety check for sensitive files with interactive prompt
- Tests for walker, parser, ranker, compressor, formatter, cache, resolver, git metadata edge cases

### Known issues

- Go import resolver does not strip module prefix from import paths — dependency graph has no edges for Go repos until `go.mod` parsing is added
- Dynamic imports and runtime-generated classes are not detected (tree-sitter is static analysis only)
- `codectx watch .` regenerates the full pipeline on every change — no incremental updates yet
- `__version__` in `__init__.py` should be read from `importlib.metadata` rather than hardcoded

---

## Next (v0.2.x)

### Ranking

- Semantic similarity ranking via `--query` — scaffolding complete, needs embedding cache invalidation on file change
- Call path analysis — multiple paths per entry point, function-level annotations in IMPORTANT_CALL_PATHS

### Parser

- Symbol cross-referencing — track where symbols defined in one file are used in others
- Improved type annotation extraction — surface return types and parameter types in structured summaries
- Constants section in structured summaries — files with no functions (config, defaults) currently emit only a purpose line

### Output

- JSON output format via `--format json` — machine-readable context for programmatic agent use
- Filter config files (pyproject.toml, package.json, Cargo.toml) from SUPPORTING_MODULES — they are not source files

### Performance

- Debounced watch mode — 3-second inactivity window before triggering regeneration, skip non-source file changes
- Incremental parse cache utilisation — only re-parse changed files on watch, patch affected CONTEXT.md sections

### Fixes

- Go resolver: parse `go.mod` to extract module name, strip it from import paths before file lookup
- `__version__` sync: read from `importlib.metadata` with fallback
- `pyproject.toml` appearing in SUPPORTING_MODULES — force config files to periphery

---

## Medium-term (v0.3.x)

### Language expansion

Swift, Kotlin, C#, PHP. Ruby support is present but shallow — improve method and module resolution.

### Advanced features

- LLM-based summarization for Tier 3 files via `--llm` flag — Anthropic and OpenAI providers already scaffolded in `compressor/summarizer.py`
- Architecture diagram export — Mermaid diagram as a standalone file, not just embedded in CONTEXT.md
- Test coverage overlay — mark untested modules in RANKED_FILES
- Detailed cyclic dependency report — currently detected but only flagged, not explained

### Multi-repository

- Monorepo support — analyze interdependent packages within a single repository root
- Cross-repo dependency graph for workspace contexts

### IDE integration

- VS Code extension — real-time context generation on save
- Neovim plugin

---

## Long-term (v1.0+)

### Agent-specific context

Role-based presets for common agent workflows — code reviewer, debugger, architect, onboarding. Each preset tunes ranking weights and output sections for the specific task an agent is performing.

### Remote analysis

- Analyze public GitHub repositories without cloning via the GitHub API
- CI/CD integration — GitHub Actions workflow that regenerates CONTEXT.md on push to main and commits it

### Semantic depth

- Data flow analysis — trace how data moves between modules
- Architectural pattern detection — identify MVC, CQRS, event-driven patterns and surface them in ARCHITECTURE section
- REST/GraphQL API extraction — identify and document API surfaces automatically

### Scale

- Streaming output — emit CONTEXT.md sections as each pipeline stage completes rather than at the end
- Distributed processing for repositories exceeding 100k files

---

## Release cadence

`v0.1.x` — stability and bug fixes  
`v0.2.x` — enhanced ranking, output formats, performance  
`v0.3.x` — language expansion, IDE integration, multi-repo  
`v1.0` — stable public API, agent-specific presets, remote analysis

Semantic versioning. Minor versions may introduce non-breaking features. No stable API guarantee until v1.0.