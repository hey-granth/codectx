---
title: FAQ
description: Frequently asked questions about codectx.
---

### Why not just use `cat *` or a simple bash script?
Simply concatenating files loses all structural hierarchy. An LLM sees thousands of lines of code with no indication of what is an entry point versus a test script. Furthermore, simple scripts won't respect `.gitignore` rules reliably, nor can they safely compress tokens when you run into context limits.

### Does `codectx` send my code to the cloud?
**No.** `codectx` runs entirely locally on your machine. It simply formats your files into a `CONTEXT.md` file. What you do with that file (e.g., send it to OpenAI, Anthropic, or an open-source local model footprint) is entirely in your control.

### What languages are supported?
Currently, due to the Tree-sitter backend, `codectx` officially supports:
- Python
- JavaScript / TypeScript
- Rust
- Go

Fallback parsing mechanisms allow it to ingest and format *any* text-based file, but the advanced Dependency Graph optimizations are limited to languages with strict parser definitions in the system.

### Can I use this in CI/CD?
Yes! Generating the `CONTEXT.md` on every PR via a GitHub action provides a highly useful, deterministic snapshot file that reviewers or automated AI code reviewers can utilize effortlessly.
