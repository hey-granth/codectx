---
title: How the Ranking System Works
description: Learn how codectx categorizes importance across a codebase.
---

When building `CONTEXT.md`, preserving context without exceeding the LLM token budget is paramount. `codectx` employs a tiered ranking system based on multiple metrics to decide which parts of the codebase matter most.

## Metrics & Weights

`codectx` calculates rank using a hybrid approach, applying a standard composite weight system to four primary metrics (normalized to `[0.0, 1.0]`):

1. **Git Frequency (40%)**: How often has the file changed?
2. **Fan-In Centrality (40%)**: How many files import this file?
3. **Recency (10%)**: How recently was this file changed in git?
4. **Entry Proximity (10%)**: How close is this file to the entry points within the module dependency graph?

If an explicit `--query` is provided, a 5th signal for **Semantic Similarity** takes up `20%` of the total weight, proportionately rescaling the initial four metrics to `80%`.

Moreover, files involved in cyclic dependency loops receive a strict `-0.10` penalty.

## Task Profiles 

You can influence how heavily the ranking factors weigh by overriding the default behavior using `--task`.

- **`default`**: Explained above.
- **`debug`**: Shifts priority mainly to recency (`0.50`), and reduces distance logic. Best for finding out why something you just edited broke.
- **`feature`**: Fan-in jumps to (`0.50`) and symbol density (`0.10`). Used to build full extensions. 
- **`architecture`**: Ignores pure recency and leverages extremely high graph dependency structure tracking (fan-in = `0.60`, entry proximity = `0.15`, directory depth = `0.10`).
- **`refactor`**: Emphasizes symbol density (`0.25`) and older recency logic.

## Percentile Tiers

The combined rankings resolve into specific distribution Tiers:

- **Tier 1 (Top 15%)**: Extremely critical code.
- **Tier 2 (Next 30%)**: Critical business logic code.
- **Tier 3 (Remaining)**: Periphery execution code.

### Non-Source Filters
Important: Specific non-source directories (e.g. `tests`, `test`, `docs`, `doc`, `examples`, `benchmarks`, `scripts`) are inherently overridden to evaluate strictly as **Tier 3** logic regardless of how many incoming connections or git modifications they possess.
