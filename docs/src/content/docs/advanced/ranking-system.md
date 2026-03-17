---
title: How the Ranking System Works
description: Learn how codectx categorizes importance across a codebase.
---

When building `CONTEXT.md`, preserving context without exceeding the LLM token budget is paramount. `codectx` employs a tiered ranking system to decide which parts of the codebase matter most.

## The Tiers

### Tier 1: Core Definitions
These are files critical to understanding the overarching architecture.
- **Entry points:** `main.py`, `app.ts`, `index.js`.
- **Architectural instructions:** `ARCHITECTURE.md`, `README.md`.
- **Primary routers:** High-level APIs and dispatchers.

### Tier 2: Logic and Implementations
These files contain the meat of the application logic but inherit importance from Tier 1.
- Models, services, controllers.
- Files that are heavily imported by many other files.

### Tier 3: Periphery
Files that are necessary for the project but usually distract LLMs when reasoning about architecture.
- Tests (e.g., `test_*.py`, `*.spec.ts`).
- Utility scripts, internal tooling, CI configs.

## Heuristics Used

`codectx` calculates rank using a hybrid approach:
1. **Explicit Identification**: Filename patterns (e.g., matching `test_` automatically down-ranks a file to Tier 3).
2. **Graph Centrality**: PageRank-style algorithms on the import graph. If ten different modules import a `logger.py`, it gets elevated.
3. **Distance to Entry Point**: Files closer to the entry point (Tier 1) in the import graph are ranked higher than files buried deep in the tree.
