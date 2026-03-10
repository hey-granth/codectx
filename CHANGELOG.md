# Changelog

All notable changes to codectx are documented here.

## [Unreleased]

### Added

- **Cache wiring** — Parse results are cached in `.codectx_cache/` using SHA-256 hashing; subsequent runs skip unchanged files.
- **Cyclic dependency detection** — Circular imports are detected via `rustworkx.digraph_find_cycle()` and listed in the `## Dependency Graph` section of `CONTEXT.md`. Files in cycles receive a scoring penalty.
- **S-expression query files** — Language-specific `.scm` query pattern files drive import/symbol extraction, with fallback to manual node-walking. Covers Python, JavaScript, TypeScript, Go, Rust, Java.
- **LLM summarization** — Optional Tier 3 file summaries via OpenAI or Anthropic (`pip install codectx[llm]`). Silently falls back to heuristic when unavailable.
- **Semantic search ranking** — Optional `--query` flag uses `lancedb` + `sentence-transformers` to boost files relevant to a natural-language query (`pip install codectx[semantic]`).
- **Multi-root support** — Analyze multiple directories with `--extra-root`. Files are labeled with their root name in the output.
- **CI cache sharing** — `codectx cache export` / `codectx cache import` for tar.gz round-tripping of `.codectx_cache/`.
