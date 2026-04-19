# Changelog

## v0.3.0 - 2026-04-19

### Added
- Persistent semantic embedding cache with hash-based invalidation in LanceDB.
- Debounced watch mode (`--debounce`) with source-file filtering and watchdog fallback behavior.
- JSON analyze output support via `--format json` and a machine-readable formatter payload.
- Go import resolver support for `go.mod` module-prefix parsing and stripping.
- Symbol cross-referencing with `symbol_ref` graph edges and exported symbol reference data.
- Constants extraction section in structured summaries for module-level assignments.
- LLM-powered summarization support in CLI with provider/model/api/base-url/max-token options.
- Config-file demotion predicate (`is_config_file`) to route manifests/configs to PERIPHERAL.

### Changed
- `codectx.__version__` now resolves using `importlib.metadata` with a local fallback.
- Project version updated to `0.3.0`.

### Dependencies
- Added runtime dependency: `watchdog>=4.0`.
- Added optional dependency: `httpx>=0.27` under `llm` extras.
- Added development dependency: `pytest-asyncio>=0.23`.

