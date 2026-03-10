# Plan

## Done
- [x] Repo scaffold + pyproject.toml
- [x] CLAUDE.md, ARCHITECTURE.md, PLAN.md, DECISIONS.md
- [x] All empty module files created

## In Progress
- [ ] `src/codectx/config/defaults.py` — constants and default values
- [ ] `src/codectx/config/loader.py` — .contextcraft.toml loader

## Next (implement in this order)

### Phase 1 — Foundation
- [ ] `src/codectx/ignore.py` — pathspec ignore handling
- [ ] `src/codectx/safety.py` — sensitive file detection + confirmation
- [ ] `src/codectx/walker.py` — file discovery pipeline

### Phase 2 — Parse
- [ ] `src/codectx/parser/languages.py` — extension → language map
- [ ] `src/codectx/parser/base.py` — ParseResult dataclass
- [ ] `src/codectx/parser/treesitter.py` — AST extraction per language

### Phase 3 — Graph
- [ ] `src/codectx/graph/resolver.py` — import string → file path per language
- [ ] `src/codectx/graph/builder.py` — rustworkx DiGraph construction

### Phase 4 — Rank
- [ ] `src/codectx/ranker/git_meta.py` — pygit2 wrappers
- [ ] `src/codectx/ranker/scorer.py` — composite scorer

### Phase 5 — Compress + Output
- [ ] `src/codectx/compressor/budget.py` — token counting with tiktoken
- [ ] `src/codectx/compressor/tiered.py` — tier assignment + budget enforcement
- [ ] `src/codectx/output/sections.py` — section constants
- [ ] `src/codectx/output/formatter.py` — markdown emitter

### Phase 6 — CLI + wiring
- [ ] `src/codectx/cli.py` — full pipeline wired via typer

### Phase 7 — Hardening
- [ ] Unit tests for scorer, compressor, ignore
- [ ] Integration test: run on codectx's own source
- [ ] Cache layer implementation
- [ ] `--watch` incremental mode
- [ ] LLM summarization opt-in (optional dep)

## Backlog
- [ ] Per-agent-role presets (debug, refactor, review)
- [ ] HTML + XML output formats
- [ ] GitHub Actions CI
- [ ] PyPI publish workflow
- [ ] Benchmark suite: token efficiency vs repomix on large repos
