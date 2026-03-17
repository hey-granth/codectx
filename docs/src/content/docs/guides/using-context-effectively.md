---
title: Using CONTEXT.md Effectively
description: Practical workflows for using CONTEXT.md with AI coding assistants.
---

`codectx` compiles your codebase into a single `CONTEXT.md` file, but the real power comes from how you use it with AI models.

## AI Coding Assistants (Cursor, Copilot, etc.)

Modern IDEs with AI features often have context limitations or struggle to autonomously locate architectural dependencies.
By feeding `CONTEXT.md` directly into the IDE's chat window, you ground the agent in reality.

**Workflow:**
1. Generate `CONTEXT.md` via `codectx analyze .`
2. Open your AI Chat and reference the file (e.g., using `@CONTEXT.md`).
3. Prompt: *"I need to add a new REST endpoint for User Profiles. Based on `@CONTEXT.md`, which routers and database schemas need to be modified?"*

The AI will output significantly more accurate answers because it has your dependency graph and core module structure explicitly laid out.

## Automated Agentic Refactoring

When building autonomous agents to refactor code, passing the raw codebase often results in circular import errors or orphaned functions.

**Workflow:**
Provide `CONTEXT.md` to your agent as its **map**.
Instead of telling the agent to "Find where X is and fix it", tell it: *"Consult your CONTEXT.md map. Find the structural tier 1 routing modules. Add dependency injection to them."*

## Codebase Exploration

When onboarding onto a new repo, `CONTEXT.md` acts as an automated README on steroids. Since it contains the dependency graphs and tiered file relevance, you can read it top-to-bottom to understand:
- What the most important files are (Tier 1 core modules).
- How the entry points map to background workers.
- What libraries are heavily utilized.
