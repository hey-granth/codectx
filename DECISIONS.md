# Architecture Decision Record

This document records major design decisions made during the development of codectx. Each decision includes context, the chosen alternative, and consequences.

## Language: Python

**Context**

We needed a language suitable for a CLI tool with quick distribution, mature AST libraries, and strong LLM SDK support.

**Decision**

Use Python as the primary implementation language.

**Consequences**

- ✅ Mature tree-sitter Python bindings available
- ✅ LLM SDKs (OpenAI, Anthropic) are Python-first
- ✅ Wide adoption among developers and AI systems
- ❌ Requires runtime (CPython 3.10+) on end-user machines
- ❌ Slightly slower than compiled alternatives (acceptable given I/O-bound nature)

*Alternatives considered:* TypeScript (less mature tree-sitter support), Rust (longer build time, friction with Python SDKs).

---

## Build Backend: Hatchling

**Context**

We needed a build backend that supports modern Python packaging standards without lock-in or excessive configuration.

**Decision**

Use Hatchling as the build backend with standard `pyproject.toml` configuration.

**Consequences**

- ✅ Zero custom configuration required
- ✅ Works seamlessly with `uv`, `pip`, `twine`
- ✅ Standard PEP 517/518 compliant
- ❌ Less opinionated than Poetry (requires manual dependency group management)

*Alternatives considered:* Poetry (lock-in with proprietary extensions), setuptools (requires extra config for src/ layout), flit (minimal but less flexible).

---

## Dependency Manager: uv

**Context**

We needed a dependency manager that is fast, standards-compliant, and suitable for distributing a Python package.

**Decision**

Use `uv` for dependency management and virtual environment handling.

**Consequences**

- ✅ Significantly faster resolver than pip/Poetry (10-100x)
- ✅ Respects standard `pyproject.toml` without extensions
- ✅ Single tool covers dependency management, building, and publishing
- ✅ Built-in support for Python version management
- ❌ Newer tool with smaller ecosystem compared to Poetry

*Alternatives considered:* Poetry (vendor lock-in, slower resolver), pip (no lock file), pipenv (abandoned).

---

## Graph Library: rustworkx

**Context**

We needed a graph library to construct dependency graphs and compute metrics like centrality and cycles. We required good performance on large graphs (10k+ nodes).

**Decision**

Use `rustworkx` for all graph operations.

**Consequences**

- ✅ Drop-in API-compatible with `networkx`
- ✅ 10-100x faster on large graphs (Rust core)
- ✅ Minimal migration cost if future switch needed
- ✅ Actively maintained
- ❌ Slightly less familiar to Python developers than `networkx`

*Alternatives considered:* networkx (pure Python, slower), igraph (different API).

---

## Git Library: pygit2

**Context**

We needed fast access to Git history data (commit frequency, recency) for file ranking. The library must not spawn subprocesses to avoid performance penalties.

**Decision**

Use `pygit2` (libgit2 bindings) for all Git operations.

**Consequences**

- ✅ Direct libgit2 bindings (no subprocess overhead)
- ✅ 5-10x faster than GitPython on large histories
- ✅ Efficient batch operations
- ❌ Requires libgit2 compiled library (usually available via system package manager)

*Alternatives considered:* GitPython (spawns git subprocess), git CLI (subprocess overhead).

---

## Parser: tree-sitter

**Context**

We needed a universal parser supporting multiple languages (Python, TypeScript, JavaScript, Go, Rust, Java). Per-language AST libraries would require duplicate implementations.

**Decision**

Use tree-sitter with language-specific grammar packages for all source code parsing.

**Consequences**

- ✅ Single, consistent interface across 6+ languages
- ✅ Fast C core
- ✅ Robust error recovery (parses incomplete/malformed code)
- ✅ Pluggable import resolvers per language
- ❌ Requires per-language grammar package (tree-sitter-python, tree-sitter-typescript, etc.)
- ❌ Different language features require different resolver implementations

*Alternatives considered:* Per-language AST libraries (ast for Python, ts-morph for TypeScript)—would require maintainable, high-quality implementations for each language.

---

## Token Counter: tiktoken

**Context**

We needed accurate token counting to enforce budget constraints. Token counts vary by LLM model; we required a solution compatible with both OpenAI and Anthropic.

**Decision**

Use `tiktoken` for all token counting.

**Consequences**

- ✅ Rust core, fast and accurate
- ✅ Covers OpenAI and Anthropic tokenization
- ✅ Minimal overhead (<50ms for large documents)
- ❌ Token counts are approximate for newer models (as of model updates)

*Alternatives considered:* transformers tokenizer (slow, GPU-dependent), manual estimation (inaccurate).

---

## CLI Framework: typer

**Context**

We needed a CLI framework that minimizes boilerplate while producing professional output with clear help messages.

**Decision**

Use Typer for all CLI command definition and parsing.

**Consequences**

- ✅ Type-hint driven (less boilerplate than Click)
- ✅ Built on Click (proven foundation)
- ✅ Rich integration for formatted output
- ✅ Automatic shell completion generation
- ❌ Fewer third-party extensions compared to Click

*Alternatives considered:* Click (more boilerplate), argparse (verbose standard library).

---

## Ignore Handling: pathspec with gitwildmatch

**Context**

We needed to respect both `.gitignore` and `.ctxignore` with exact behavioral parity with Git's own ignore logic.

**Decision**

Use `pathspec` with `gitwildmatch` semantics for all ignore pattern matching.

**Consequences**

- ✅ Exact parity with Git's ignore behavior
- ✅ No edge case differences between our implementation and Git's
- ✅ Users understand patterns (familiar from `.gitignore`)
- ✅ Supports `.ctxignore` extension without reinventing syntax

*Alternatives considered:* Custom glob implementation (error-prone, subtle behavioral differences).

---

## Project Layout: src/

**Context**

We needed to prevent accidental imports of the uninstalled package during development and follow best practices for PyPI distributions.

**Decision**

Use src/ layout with package code in `src/codectx/`.

**Consequences**

- ✅ Prevents import of uninstalled package
- ✅ Standard for packages intended for PyPI distribution
- ✅ Forces explicit installation during development
- ❌ Slightly more verbose than flat layout
- ❌ Requires explicit configuration in pyproject.toml for build backend

*Alternatives considered:* Flat layout (simpler but risks unintended imports).

---

## Optional Dependencies: LLM Extras

**Context**

Core functionality (codebase analysis and compression) does not require LLM integrations. However, some advanced features (code summarization) benefit from LLM access. Users should be able to use the tool without API keys.

**Decision**

Make LLM dependencies (OpenAI, Anthropic SDKs) optional via `pip install codectx[llm]`.

**Consequences**

- ✅ Tool is usable without API credentials
- ✅ Users opt into LLM features explicitly
- ✅ Reduced dependencies for basic usage
- ❌ Users must remember to install extras for advanced features

*Alternatives considered:* Require all dependencies (forces API key requirement).

---

## Configuration Format: TOML

**Context**

We needed a configuration file format that is readable, standard, and integrates well with Python packaging tools.

**Decision**

Use TOML format for `.codectx.toml` configuration files, following PEP 518 conventions.

**Consequences**

- ✅ Human-readable and widely understood
- ✅ Standard for Python packaging (pyproject.toml)
- ✅ Minimal parsing library required (tomli/tomllib)
- ✅ No custom schema language needed

*Alternatives considered:* YAML (less structured), JSON (less readable).

