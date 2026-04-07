---
title: Basic Usage
description: Common commands and options when using codectx.
---

The `codectx` CLI provides powerful features for different workflows.

## The `analyze` Command

The core command you will use most often is `analyze`:

```bash
codectx analyze <path>
```

### Controlling Output Size

LLMs have finite context windows. To ensure your context fits cleanly, use the `--tokens` flag (default: 120,000). 
`codectx` will intelligently compress files to fit this budget.

```bash
codectx analyze . --tokens 60000
```

### Task Profiles

You can bias the ranking algorithm toward the task your AI agent is performing using the `--task` flag. The available profiles are:
- `default` — Balanced overview of the project architecture
- `debug` — Bias toward recently modified files and entry points
- `feature` — Bias heavily toward heavily imported modules (fan-in) and high symbol density
- `architecture` — Focus purely on structural connections and distance from entry points
- `refactor` — Highlight high fan-in and dense modules while ignoring recency

```bash
codectx analyze . --task debug
```

### Semantic Search Ranking

You can provide a semantic query describing the area you want to focus on using `--query`. This requires the `[semantic]` extra to be installed (`pip install codectx[semantic]`).

```bash
codectx analyze . --query "authentication middleware and login flow"
```

### Including Recent Changes

If you want the agent to focus on what you've just been working on, you can include recent git changes using the `--since` flag:

```bash
codectx analyze . --since "2 days ago"
```

## Watching for Changes

If you're iterating locally alongside an agent, you can have `codectx` continually update the file as you code:

```bash
codectx watch .
```

For a comprehensive list of all commands (including `benchmark` and `search`) and flags, see the [CLI Reference](../../reference/cli-reference/).
