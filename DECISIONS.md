# Decisions

Settled architectural decisions. Do not re-litigate without a concrete reason.

---

## Language: Python
**Chosen over:** TypeScript, Rust
**Reason:** tree-sitter Python bindings are mature. LLM SDKs are Python-first.
Rust would win on distribution speed but not worth friction at this stage.
Distribution solved via uv/uvx.

---

## Build backend: hatchling
**Chosen over:** Poetry, setuptools, flit
**Reason:** Poetry is lock-in with proprietary pyproject.toml sections.
setuptools requires extra config for src/ layout. hatchling is minimal and standard.

---

## Dependency manager: uv
**Chosen over:** Poetry, pip, pipenv
**Reason:** Faster resolver, standard pyproject.toml, covers install + build + publish.
Replaces Poetry entirely with no downside.

---

## Graph library: rustworkx
**Chosen over:** networkx
**Reason:** Drop-in API compatible with networkx. Rust core. 10-100x faster on large graphs.
No migration cost from networkx if we ever need to switch.

---

## Git library: pygit2
**Chosen over:** gitpython
**Reason:** libgit2 bindings. Significantly faster than gitpython for log/blame traversal.
gitpython spawns subprocesses; pygit2 does not.

---

## Parser: tree-sitter
**Chosen over:** language-specific AST libraries (ast, ts-morph, go/parser)
**Reason:** Universal. Single interface across all languages. C core is fast.
Per-language AST libs would require a different implementation per language — unmaintainable.

---

## Token counter: tiktoken
**Chosen over:** manual estimation, transformers tokenizer
**Reason:** Rust core, fast, accurate for OpenAI and Anthropic models.
Model-agnostic enough for our purposes.

---

## CLI framework: typer
**Chosen over:** click, argparse
**Reason:** Built on click. Type-hint driven. Less boilerplate. Rich integration built in.

---

## Ignore handling: pathspec with gitwildmatch
**Chosen over:** custom glob implementation
**Reason:** Exact behavioral parity with git's own ignore processing.
No edge case differences between .gitignore and .ctxignore handling.

---

## src/ layout
**Chosen over:** flat layout
**Reason:** Prevents import of uninstalled package during development.
Standard for packages intended for PyPI distribution.

---

## LLM summarization: optional dependency
**Chosen over:** required dependency
**Reason:** Core tool must work without any LLM API key.
Summarization is an enhancement, not a requirement.
Users opt in via `pip install codectx[llm]`.
