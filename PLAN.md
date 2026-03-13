# Roadmap

This document outlines the current capabilities and planned improvements for codectx.

## Current Capabilities (v0.1.x)

### Core Pipeline

- ✅ Repository scanning with `.gitignore` and `.ctxignore` support
- ✅ Parallel AST parsing using tree-sitter
- ✅ Dependency graph construction (rustworkx)
- ✅ File ranking using composite scoring (git frequency, dependency centrality, recency)
- ✅ Token-aware compression with tier-based truncation
- ✅ Structured markdown output (CONTEXT.md)
- ✅ Deterministic output across runs

### Language Support

- ✅ Python
- ✅ TypeScript / JavaScript
- ✅ Go
- ✅ Rust
- ✅ Java
- ✅ C / C++
- ✅ Ruby

### CLI Features

- ✅ `codectx analyze .` — generate context
- ✅ `codectx watch .` — incremental mode
- ✅ Custom token budget (`--tokens`)
- ✅ Custom output path (`--output`)
- ✅ Recent changes section (`--since`)
- ✅ Verbose logging (`--verbose`)

### Configuration

- ✅ `.contextcraft.toml` support
- ✅ CLI flag overrides
- ✅ Configuration precedence

### Quality Assurance

- ✅ Unit tests for core modules (parser, ranker, compressor)
- ✅ Integration tests on real repositories
- ✅ Type checking (mypy strict mode)
- ✅ Linting (ruff)

---

## Short-term Improvements (v0.2.x)

### Enhanced Ranking

- [ ] **Semantic similarity ranking** — optional embedding-based file importance using `sentence-transformers` and `lancedb`
- [ ] **Task-aware context** — adjust ranking weights based on task type (debug, feature, architecture, refactor)
- [ ] **Call path analysis** — identify and highlight critical execution flows from entry points

### Parser Improvements

- [ ] **Symbol cross-referencing** — track symbol definitions and usages across files
- [ ] **Docstring extraction** — improved extraction and formatting of docstrings
- [ ] **Type annotation analysis** — extract type signatures for better function understanding

### Output Enhancements

- [ ] **HTML output format** — generate interactive HTML version of CONTEXT
- [ ] **JSON output format** — machine-readable context export
- [ ] **Symbol index** — comprehensive searchable list of functions, classes, methods

### Performance

- [ ] **Incremental caching improvements** — smarter invalidation strategy
- [ ] **Parallel graph operations** — parallelize dependency resolution
- [ ] **Memory optimization** — reduce peak memory usage on very large repositories

---

## Medium-term Improvements (v0.3.x)

### Language Expansion

- [ ] **Swift** — iOS/macOS codebases
- [ ] **Kotlin** — JVM/Android support
- [ ] **C#** — .NET ecosystem
- [ ] **PHP** — Web applications
- [ ] **Ruby** — better Ruby support

### Advanced Features

- [ ] **Code summarization** — automatic summary generation using LLMs (optional dependency)
- [ ] **Module search** — natural language module search via semantic embeddings
- [ ] **Architecture diagrams** — auto-generate module architecture diagrams
- [ ] **Test coverage analysis** — highlight untested modules
- [ ] **Cyclic dependency warnings** — detailed reports on circular dependencies

### IDE Integration

- [ ] **VS Code extension** — real-time context generation
- [ ] **JetBrains plugin** — PyCharm / IntelliJ integration
- [ ] **Neovim integration** — Lua plugin for vim users

### Multi-repository Support

- [ ] **Monorepo handling** — analyze interdependent modules across multiple repositories
- [ ] **Cross-repo dependency graphs** — trace imports across project boundaries
- [ ] **Workspace contexts** — generate context for multiple related projects

---

## Long-term Vision (v1.0+)

### Agent-Specific Context Generation

- [ ] **Role-based presets** — pre-configured context profiles for different agent roles (code reviewer, debugger, architect)
- [ ] **Agent-specific formatting** — context shaped for specific LLM APIs (OpenAI, Anthropic, open-source models)
- [ ] **Agentic workflows** — integration with frameworks like CrewAI, LangChain

### Distributed Analysis

- [ ] **Remote repository analysis** — analyze GitHub repositories without cloning
- [ ] **CI/CD integration** — automatic context generation in GitHub Actions, GitLab CI
- [ ] **Context versioning** — maintain historical context snapshots aligned with releases

### Advanced Semantics

- [ ] **Intent detection** — infer module purpose from code patterns
- [ ] **Architectural patterns** — identify and document common patterns (MVC, CQRS, etc.)
- [ ] **Data flow analysis** — trace data flow between modules
- [ ] **Security analysis** — flag potential security issues for agent review

### Ecosystem Integration

- [ ] **PyPI metadata extraction** — incorporate package documentation
- [ ] **GitHub integration** — use repository metadata (stars, contributors, activity)
- [ ] **Documentation parsing** — extract and incorporate existing README, docs
- [ ] **API schema extraction** — identify and document REST/GraphQL APIs

### Performance at Scale

- [ ] **Distributed processing** — handle 100k+ file repositories efficiently
- [ ] **Streaming output** — progressive context generation (output CONTEXT.md as pipeline stages complete)
- [ ] **Compression algorithms** — improved compression strategies beyond token counting

---

## Known Limitations & Future Work

### Current Limitations

- **Import resolution:** Cross-language imports (e.g., Python calling C extensions) are not traced
- **Dynamic imports:** Runtime-generated imports are not detected
- **Monorepo support:** Single repository analysis only
- **Configuration:** No per-module ignore rules or context weights

### Backlog (No Current Timeline)

- [ ] Benchmark suite comparing token efficiency vs. competing tools
- [ ] Docker image for CI/CD integration
- [ ] Web UI for interactive context exploration
- [ ] Commercial hosting service for large-scale analysis
- [ ] Academic research on LLM context optimization

---

## Release Cadence

- **v0.1.x** — Stability, bug fixes, parser improvements
- **v0.2.x** — Enhanced ranking, output formats, performance
- **v0.3.x** — Language expansion, IDE integration, multi-repo support
- **v1.0** — Agent-specific context generation, stable API guarantee

Releases follow semantic versioning. Minor versions (v0.x.y) may introduce non-breaking new features. Patch versions fix bugs.

