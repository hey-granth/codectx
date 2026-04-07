---
title: What is codectx?
description: An overview of the codectx CLI tool and its purpose.
---

`codectx` is a powerful, deterministic CLI tool designed to compile an entire codebase into a single, highly-structured `CONTEXT.md` file explicitly optimized for AI coding agents such as Claude, GPT-4, and Gemini. 

Modern AI coding workflows rely on context. However, simply feeding raw files into an AI model often results in dropped connections, hallucinations, and wasted tokens due to disorganization. `codectx` bridges this gap.

It analyzes your project structure, computes dependency graphs, categorizes files by importance, and formats everything logically so that an LLM can immediately understand the architecture and operational flow of your project.

## Key Features

- **Tiered Ranking System**: Automatically categorizes files into core components, supporting logic, and utility scripts based on structural importance.
- **Dependency Graph Awareness**: Maps out how different parts of your codebase depend on one another.
- **Token Budgeting**: Respects hard token limits by intelligently compressing files and stripping non-essential artifacts when constraints are met.
- **Structured Output**: Generates predictable, well-formatted Markdown blocks ensuring reproducible prompts for autonomous agents.

*Benchmark Note: In internal testing across 5 common open-source repositories, codectx achieved an average token reduction of 76% compared to raw file concatenation while preserving all critical architectural signals.*

Explore the [Quick Start](../getting-started/quick-start/) to generate your very first context file!
