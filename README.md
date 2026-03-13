# codectx — Codebase Context Compiler for AI Agents

codectx compiles a repository into a structured `CONTEXT.md` file optimized for AI coding agents.

Instead of feeding raw repositories to an AI system, codectx analyzes the project structure, identifies important modules, and produces a high-signal context document designed for efficient reasoning.

---

# Overview

Modern AI coding agents struggle with large repositories.

Raw codebases contain thousands of files, unclear entry points, and hidden dependency relationships. Feeding this directly to an AI model results in:

- poor signal-to-noise ratio
- wasted context window tokens
- agents missing critical modules
- inaccurate reasoning about the system

codectx solves this by **treating context generation as a compilation process**.

The tool analyzes the repository, ranks files by importance, compresses code intelligently, and emits a structured `CONTEXT.md` designed specifically for AI agents.

---

# Quick Start

```bash
codectx analyze .
```

This analyzes the current repository and generates a single structured context file:

```
CONTEXT.md
```

You can customize the analysis with advanced flags:

```bash
# Optimize context for a specific task (debug, feature, architecture)
codectx analyze . --task debug

# Generate multi-layer context files (REPO_MAP.md, CORE_CONTEXT.md)
codectx analyze . --layers
```

You can then provide `CONTEXT.md` (or the layered files) to your AI coding agent as highly focused structured repository context.

---

# Why codectx exists

Most tools that prepare code for AI agents simply:

* concatenate repository files
* generate shallow summaries
* ignore dependency relationships

This causes several problems:

**Poor signal-to-noise ratio**
Core architecture is buried under utilities and boilerplate.

**Inefficient token usage**
Agents spend context window tokens on irrelevant modules.

**Weak reasoning about dependencies**
Without structural information, agents struggle to trace execution flow.

codectx addresses this by analyzing repositories as **systems of dependencies**, not collections of files.

---

# How codectx works

codectx processes repositories through a structured pipeline:

```
Repository
    │
    ▼
Walker
    │
    ▼
Parser
    │
    ▼
Dependency Graph
    │
    ▼
Ranker
    │
    ▼
Compressor
    │
    ▼
Formatter
    │
    ▼
CONTEXT.md
```

### Walker

Discovers repository files while respecting `.gitignore` and `.ctxignore`.

### Parser

Extracts imports, symbols, and signatures using tree-sitter.

### Dependency Graph

Builds a directed graph of module relationships.

### Ranker

Scores files using graph centrality and git metadata.

### Compressor

Fits the most relevant code into a strict token budget.

### Formatter

Generates a structured `CONTEXT.md` optimized for AI agents.

---

# Key Features

* automatic repository analysis
* dependency graph and critical call path construction
* semantic relevance scaling and search using `lancedb`
* task-aware context weighting (debug, feature, architecture)
* multi-layer context generation (`--layers`)
* performance and budget telemetry
* deterministic output
* multi-language parsing

Supported languages include:

* Python
* TypeScript
* JavaScript
* Go
* Rust
* Java

---

# Installation

codectx requires **Python 3.10+**.

Until the package is published on PyPI, install it from source.

### Clone the repository

```bash
git clone https://github.com/hey-granth/codectx.git
cd codectx
```

### Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install in development mode

```bash
pip install -e .
```

You can now run:

```bash
codectx analyze .
```

---

# CLI Commands

### Generate context

```bash
codectx analyze .
```

Generates `CONTEXT.md` for the current repository. You can append `--task [debug|feature|architecture]` to adjust the ranking heuristics, or `--layers` to write separate files (`REPO_MAP.md`, `CORE_CONTEXT.md`) alongside the full context.

---

### Semantic Search

```bash
codectx search "authentication logic" --root .
```

Leverages `sentence-transformers` and `LanceDB` to find the most semantically relevant files for a natural language query, returning a ranked list with relevance scores.

---

### Benchmark repository analysis

```bash
codectx benchmark .
```

Shows detailed performance statistics for each pipeline stage.

---

### Watch repository changes

```bash
codectx watch .
```

Automatically regenerates `CONTEXT.md` whenever files change.

---

# Output Format

The generated `CONTEXT.md` contains structured sections designed for AI reasoning.

### ARCHITECTURE

High-level project structure and auto-generated description.

### ENTRY_POINTS

Main execution paths and public interfaces.

### SYMBOL_INDEX

Comprehensive list of top-level code symbols (classes, functions, methods) to provide rapid overview.

### IMPORTANT_CALL_PATHS

Traces of critical execution paths starting from entry points deep into the dependency graph.

### CORE_MODULES

Full source code for the most important logic.

### SUPPORTING_MODULES

Compressed signatures and docstrings for secondary modules.

### DEPENDENCY_GRAPH

Mermaid graph showing module relationships and cyclic dependency warnings.

### PERIPHERY

One-line summaries of remaining files.

---

# Example Workflow

1. Clone a repository.

```
git clone https://github.com/USERNAME/PROJECT.git
cd PROJECT
```

2. Generate context.

```
codectx analyze .
```

3. Provide `CONTEXT.md` to your AI coding agent.

4. Run development tasks with significantly improved context.

---

# When to use codectx

codectx is useful when:

* preparing context for AI coding agents
* exploring unfamiliar repositories
* reducing prompt token usage
* improving AI code generation accuracy

---

# Design Principles

codectx follows several core engineering principles:

**Deterministic output**
Identical repositories produce identical context.

**High signal-to-noise ratio**
Important modules are prioritized.

**Token efficiency**
Context windows are used efficiently.

**Language-agnostic parsing**
Tree-sitter ensures consistent behavior across languages.

**Modular architecture**
Each pipeline stage is independently extensible.

---

# Contributing

Contributions are welcome.

The project prioritizes:

* correctness
* performance
* maintainability

See `ARCHITECTURE.md` for internal design details.

---

# License

MIT License

