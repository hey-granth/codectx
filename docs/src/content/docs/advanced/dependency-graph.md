---
title: Dependency Graph Design
description: Inside the AST parser and import graph analyzer.
---

AI coding models are highly proficient at isolated logic problems, but they struggle heavily with interconnected systems. Passing code files linearly is a major cause of hallucinations.

`codectx` injects a visual representation of your Dependency Graph directly into `CONTEXT.md`.

## How it's Built

1. **Tree-sitter AST**: `codectx` utilizes Tree-sitter, an incredibly fast incremental parsing system. We use S-expression queries (like `(import_statement)`) to specifically target connections between files without running or fully interpreting the code.
2. **Path Normalization**: The crawler converts all relative and aliased imports into normalized absolute paths within the repository.
3. **Graph Rendering**: The backend uses an undirected graph topology. It groups files into highly connected clusters and renders an ASCII representation of the connections for the LLM.

## Why it works for LLMs

Models like Claude and GPT-4 process sequential text. When presented with a graph as markdown structured text, they can "trace" variable flow backwards to its source conceptually *before* they even begin generating their response, significantly improving response accuracy on complex structural changes.
