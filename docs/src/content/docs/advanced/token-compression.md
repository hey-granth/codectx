---
title: Token Compression Strategy
description: How codectx ensures your context fits within limits.
---

Providing a `--tokens [MAX]` flag enables the `codectx` compression engine, capping execution out perfectly to the budget. The compression engine processes files based strictly on the Tier levels established in the ranking engine.

## Tier Details

### 1. Tier 1: Key Metadata
Instead of full source reproduction, `codectx` emits an AST-driven **structured summary** representing the overall footprint natively derived from its core definitions. This includes its exact purpose, what valid variables/internal dependencies it leverages, types, function headers, signatures, and behavioral notes out-of-the-norm (`async-heavy`). The *only* source files evaluated functionally end-to-end to `300` lines (max) are strict entry points (e.g. `main.py`).

### 2. Tier 2: Interface Collapsing
Tier 2 emits exact function and class signatures alongside docstrings. Everything within the body scope of `def`/`class` implementations is intentionally discarded.

### 3. Tier 3: One Line Summary
Tier 3 simply includes an exact heuristic statement of its functionality. Ex: "10 classes, 15 lines".

## The Budget Priority
Budget gets consumed through evaluating Tier 1 first, descending across its internal scores. It moves through Tier 2 down into Tier 3.

```text
[Tokens] -> Tier 1 Output -> Tier 2 Output -> Tier 3 Output
```

If budget truncates along the threshold flow, we abandon any remaining Tier 3 elements, truncate Tier 2 elements natively across the file buffer bounds, all the way to trimming existing parsed summaries.
