---
title: Best Practices
description: How to structure your project to get the best results from codectx.
---

`codectx` applies deterministic heuristics to rank your codebase. To ensure it accurately builds your `CONTEXT.md`, follow these repository best practices:

## 1. Maintain Clear Module Boundaries

`codectx` relies on import parsing and folder structures to build its dependency graph. If your project uses flat architectures with "god files" containing thousands of lines, `codectx` cannot efficiently summarize or compress them.

- **Prefer smaller, descriptive files.**
- **Group related files in logical directories.**

## 2. Keep Architecture Documentation Updated

`codectx` automatically elevates architectural documentation (like `ARCHITECTURE.md` or `.github/workflows`) into the Core context tier.

Ensure these files are concise and accurate. The LLM will read them first before reading your code, effectively using them as the instruction manual for your application state.

## 3. Regularize Entry Points

`codectx` looks for common entry point patterns (like `main.py`, `src/index.js`, `__main__.py`, etc.). Ensuring your application starts cleanly from an easily identifiable entry point allows the dependency graph traversal to be highly accurate.

## 4. Use Continuous Generation in Workflows

Integrate `codectx` into your pre-commit hooks or watch processes:

```bash
codectx watch . 
```

This guarantees that if your agent acts on the `CONTEXT.md`, it's not looking at a stale representation of your codebase.
