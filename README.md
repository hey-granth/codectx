# codectx

[![PyPI](https://img.shields.io/pypi/v/codectx)](https://pypi.org/project/codectx/)
[![Python](https://img.shields.io/pypi/pyversions/codectx)](https://github.com/hey-granth/codectx)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/hey-granth/codectx/blob/main/LICENSE)

A CLI tool that analyzes a repository and generates a structured `CONTEXT.md` file optimized for AI coding agents.

## Overview

### Problem

Large codebases are difficult for AI agents to reason about. Raw repositories contain thousands of files with unclear entry points and hidden dependency relationships. Feeding unstructured code directly to an AI model results in:

- Poor signal-to-noise ratio—critical logic buried under utilities and boilerplate
- Wasted context window tokens—agents spend budget on irrelevant modules
- Weak reasoning about dependencies—agents cannot trace execution flow without structural information

### Solution

codectx treats context generation as a **compilation process**. It analyzes your repository, ranks files by importance using dependency graphs and git metadata, compresses code intelligently to a token budget, and emits a structured markdown document designed specifically for AI systems.

The result is a high-signal context file that helps AI agents understand architecture and make better engineering decisions.

## Key Features

- **Fast codebase scanning** — respects `.gitignore` and `.ctxignore` patterns
- **Dependency graph analysis** — constructs module relationships and identifies critical paths
- **Token-aware compression** — enforces hard token budget with intelligent truncation
- **Language-agnostic parsing** — tree-sitter supports Python, TypeScript, JavaScript, Go, Rust, Java, and more
- **Deterministic output** — identical repositories produce identical context
- **Incremental mode** — watch filesystem and regenerate on changes
- **High-signal ranking** — scores files by git frequency, dependency centrality, and recency

## Installation

codectx requires **Python 3.10+** and is distributed through PyPI.

### Using `pip`

```bash
pip install codectx
```

### Using `uv`

```bash
uv add codectx
```

### From source (development)

```bash
git clone https://github.com/hey-granth/codectx.git
cd codectx
pip install -e ".[dev]"
```

## Usage

### Basic analysis

Generate a context file for the current repository:

```bash
codectx analyze .
```

This produces `CONTEXT.md` with the following sections:

- **ARCHITECTURE** — High-level project structure
- **ENTRY_POINTS** — Main execution paths and public APIs
- **CORE_MODULES** — Full source for the most important files
- **SUPPORTING_MODULES** — Compressed signatures and docstrings
- **DEPENDENCY_GRAPH** — Mermaid diagram of module relationships
- **PERIPHERY** — One-line summaries of remaining files

### Custom token budget

Adjust the context window size:

```bash
codectx analyze . --tokens 60000
```

### Custom output path

```bash
codectx analyze . --output my-context.md
```

### Watch mode

Automatically regenerate context on file changes:

```bash
codectx watch .
```

### Recent changes

Include a diff section for changes within a time window:

```bash
codectx analyze . --since "7 days ago"
```

## Output Format

The generated `CONTEXT.md` is structured with fixed sections optimized for AI reasoning:

### ARCHITECTURE

Auto-generated project description and high-level structure.

### DEPENDENCY_GRAPH

Mermaid diagram showing module relationships. Flags cyclic dependencies.

### ENTRY_POINTS

Main files and public interfaces—full source code.

### CORE_MODULES

Important modules based on dependency centrality and git history—full source.

### SUPPORTING_MODULES

Secondary modules—function signatures and docstrings only.

### PERIPHERY

Remaining files—module name and one-line summary.

### RECENT_CHANGES

Optional section showing git diff since a specified date.

## Development

### Setup

Install dev dependencies:

```bash
pip install -e ".[dev]"
```

### Running tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=src/codectx
```

### Type checking

```bash
mypy src
```

### Code formatting

```bash
ruff format src tests
```

### Linting

```bash
ruff check src tests
```

## How It Works

codectx processes repositories through a structured pipeline:

```
Repository
    ↓
[Walker]       → Scan files, apply .gitignore
    ↓
[Parser]       → Extract imports and symbols via tree-sitter
    ↓
[Graph]        → Build dependency graph
    ↓
[Ranker]       → Score files by importance
    ↓
[Compressor]   → Fit content to token budget
    ↓
[Formatter]    → Emit structured markdown
    ↓
CONTEXT.md
```

For a detailed explanation of each stage, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Design Principles

**Deterministic output** — Identical repositories produce identical context across runs.

**High signal-to-noise ratio** — Critical modules are prioritized; boilerplate is deprioritized.

**Token efficiency** — Every token in the output is optimized for usefulness.

**Language-agnostic** — tree-sitter enables consistent parsing across six+ languages.

**Modular architecture** — Each pipeline stage is independently extensible.

See [DECISIONS.md](DECISIONS.md) for the reasoning behind key architectural choices.

## Configuration

codectx respects a `.contextcraft.toml` file in the project root:

```toml
[codectx]
token_budget = 120000
output = "CONTEXT.md"
include_patterns = ["src/**", "lib/**"]
exclude_patterns = ["tests/**", "*.test.py"]
```

CLI flags override configuration file values.

## Contributing

Contributions are welcome. The project prioritizes:

- Correctness
- Performance
- Maintainability

Please file issues for bugs or feature requests.

## License

MIT License. See [LICENSE](LICENSE) for details.

