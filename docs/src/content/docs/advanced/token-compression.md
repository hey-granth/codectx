---
title: Token Compression Strategy
description: How codectx ensures your context fits within limits.
---

Providing a `--tokens [MAX]` flag enables the `codectx` compression engine. This is heavily optimized to safely pack as much structural context as possible without breaking the LLM's understanding.

## Compression Flow

When the raw `CONTEXT.md` size exceeds the maximum requested tokens, the following steps execute sequentially until the budget is met:

### 1. Periphery Pruning (Tier 3)
The engine removes the implementation details of Tier 3 files entirely. 
*Instead of providing a 500-line test file, it only lists the filename in the Tree structure.*

### 2. Comment Stripping
Inline comments and docstrings in Tier 2 files are stripped using AST parsing (respecting the syntax tree, not just regex). This dramatically drops token counts while keeping raw structural code intact.

### 3. Interface Collapsing
If the budget is still exceeded, `codectx` collapses Tier 2 files into strictly their interface definitions (class signatures, function headers, exported types) removing the internal function bodies entirely.

By applying these sequentially, the LLM retains maximum context about *what* the system does and *how* it connects, only losing *implementation details* when absolutely necessary.
