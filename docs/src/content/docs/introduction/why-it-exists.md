---
title: Why it exists
description: The philosophy and engineering problems codectx solves.
---

The transition to agentic AI coding assistants has revealed a fundamental limitation: **context window efficiency.**

While models now have large context windows (100k - 200k+ tokens), throwing an entire raw codebase into the prompt is highly inefficient. Models struggle with "needle in a haystack" retrieval problems when information isn't structured logically.

We built `codectx` because we needed a way to:

### 1. Reduce Noise
Not all files are created equal. An interface definition is structurally more important than a test mock. `codectx` figures out what matters most.

### 2. Supply Architecture, Not Just Code
LLMs are excellent at writing functions but often fail to grasp the broader system architecture. By computing dependency graphs, `codectx` provides the system's blueprint alongside the code. 

### 3. Ensure Predictability
When interacting with AI continuously across branches, you need consistent, deterministic inputs. A highly engineered, reproducible context snapshot guarantees that identical codebases yield identical prompts every single time.
