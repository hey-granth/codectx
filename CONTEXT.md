## ARCHITECTURE

# Architecture

## Problem
AI agents receive poor codebase context because existing tools (repomix, etc.) are file
concatenators. They dump files in filesystem order with no ranking, no compression, and no
semantic structure. Agent output quality is bounded by signal-to-noise ratio in the context window.

## Solution
Treat context generation as compilation. Parse the codebase into a dependency graph, rank files
by importance signals, compress to a token budget, and emit structured output that orients an
agent immediately.

## Pipeline

```
Codebase
  │
  ▼
Walker
  - Recursive file discovery from root
  - Applies ALWAYS_IGNORE, .gitignore, .ctxignore in order
  - Warns and confirms on sensitive file detection
  - Returns: List[Path]
  │
  ▼
Parser (parallel, ProcessPoolExecutor)
  - Detects language from file extension
  - Extracts via tree-sitter AST:
      - Import statements → List[str]
      - Top-level symbols (functions, classes) → List[Symbol]
      - Docstrings per symbol
  - Returns: Dict[Path, ParseResult]
  │
  ▼
Graph Builder
  - Resolves import strings → file paths (per-language resolver)
  - Constructs rustworkx DiGraph: nodes=files, edges=imports
  - Computes fan-in (in-degree) per node
  - Returns: DepGraph
  │
  ▼
Ranker
  - Scores each file 0.0–1.0 using weighted composite:
      git_frequency  : 0.35  (commit count touching file)
      fan_in         : 0.35  (how many files import this)
      recency        : 0.20  (days since last modification)
      entry_proximity: 0.10  (graph distance from entry points)
  - Returns: Dict[Path, float]
  │
  ▼
Compressor
  - Enforces token budget (from config or CLI flag)
  - Assigns tier per file by score:
      Tier 1 (score > 0.7): full source
      Tier 2 (score 0.3–0.7): signatures + docstrings
      Tier 3 (score < 0.3): one-line summary
  - If over budget: drop Tier 3 → truncate Tier 2 → truncate Tier 1
  - Returns: Dict[Path, CompressedFile]
  │
  ▼
Formatter
  - Emits structured markdown with fixed section order
  - Sections: ARCHITECTURE, DEPENDENCY_GRAPH, ENTRY_POINTS,
              CORE_MODULES, PERIPHERY, RECENT_CHANGES
  - Returns: str
  │
  ▼
Output file (default: context.md)
```

## Parallelism model
- File parsing: ProcessPoolExecutor (CPU-bound, tree-sitter C extension)
- File I/O: ThreadPoolExecutor (I/O-bound, reading source files)
- Graph construction: single-threaded (fast, rustworkx handles it)
- Ranking: single-threaded (fast after git metadata collected)

## Caching
- Cache key: (file_path, file_hash, git_commit_sha)
- Cache location: .codectx_cache/ at project root (gitignored)
- Cached: ParseResult per file, git metadata per file
- Invalidated: on file content change or new commit

## Incremental mode (--watch)
- watchfiles monitors project root
- On change: reparse affected files only
- Rebuild graph for changed nodes and their dependents
- Re-rank affected subgraph
- Re-emit output

## Token budget enforcement
Hard cap. Not a suggestion. Budget is consumed in this order:
1. ARCHITECTURE section (fixed, small)
2. DEPENDENCY_GRAPH section (fixed, small)
3. Tier 1 files by rank score descending
4. Tier 2 files by rank score descending
5. Tier 3 files by rank score descending

Files that don't fit are omitted with a note in the output.

## Language support
Pluggable resolver interface. Initial support:
- Python (.py)
- TypeScript (.ts, .tsx)
- JavaScript (.js, .jsx)
- Go (.go)
- Rust (.rs)
- Java (.java)

Adding a language requires: tree-sitter grammar (via tree-sitter-languages) + import resolver.

## Config precedence
CLI flags > .contextcraft.toml > defaults


## DEPENDENCY_GRAPH

```mermaid
graph LR
    f0["src/codectx/cli.py"]
    f1["src/codectx/parser/base.py"]
    f2["src/codectx/walker.py"]
    f3["src/codectx/parser/treesitter.py"]
    f4["src/codectx/cache.py"]
    f5["src/codectx/config/loader.py"]
    f6["src/codectx/graph/builder.py"]
    f7["src/codectx/config/defaults.py"]
    f8["src/codectx/output/formatter.py"]
    f9["src/codectx/compressor/tiered.py"]
    f10["src/codectx/ranker/git_meta.py"]
    f11["src/codectx/graph/resolver.py"]
    f12["tests/test_walker.py"]
    f13["tests/test_parser.py"]
    f14["pyproject.toml"]
    f15["src/codectx/ranker/semantic.py"]
    f16["src/codectx/ranker/scorer.py"]
    f17["tests/unit/test_cache_export.py"]
    f18["tests/unit/test_cache_wiring.py"]
    f19["tests/unit/test_semantic.py"]
    f20["tests/unit/test_formatter_sections.py"]
    f21["tests/test_scorer.py"]
    f22["tests/unit/test_cycles.py"]
    f23["tests/unit/test_summarizer.py"]
    f24["src/codectx/compressor/budget.py"]
    f25["requirements.txt"]
    f26["src/codectx/parser/languages.py"]
    f27["tests/test_integration.py"]
    f28[".gitignore"]
    f29["main.py"]
    f30["src/codectx/compressor/summarizer.py"]
    f31["src/codectx/ignore.py"]
    f32["tests/unit/test_multi_root.py"]
    f33["tests/test_compressor.py"]
    f34["src/codectx/safety.py"]
    f35["src/codectx/parser/queries/go.scm"]
    f36["src/codectx/parser/queries/java.scm"]
    f37["src/codectx/parser/queries/javascript.scm"]
    f38["src/codectx/parser/queries/python.scm"]
    f39["src/codectx/parser/queries/rust.scm"]
    f40["src/codectx/parser/queries/typescript.scm"]
    f41["tests/unit/__init__.py"]
    f42["tests/unit/test_queries.py"]
    f43["src/codectx/__init__.py"]
    f44["src/codectx/compressor/__init__.py"]
    f45["src/codectx/config/__init__.py"]
    f46["src/codectx/graph/__init__.py"]
    f47["src/codectx/output/__init__.py"]
    f48["src/codectx/output/sections.py"]
    f49["src/codectx/parser/__init__.py"]
    f4 --> f1
    f4 --> f7
    f6 --> f1
    f6 --> f11
    f6 --> f7
    f12 --> f2
    f13 --> f3
    f17 --> f0
    f17 --> f5
    f17 --> f4
    f18 --> f0
    f18 --> f5
    f19 --> f0
    f19 --> f5
    f19 --> f16
    f19 --> f10
    f19 --> f6
    f19 --> f15
    f19 --> f1
    f20 --> f8
    f20 --> f6
    f20 --> f9
    f20 --> f24
    f21 --> f16
    f21 --> f10
    f21 --> f6
    f22 --> f1
    f22 --> f6
    f23 --> f9
    f23 --> f24
    f23 --> f30
    f23 --> f1
    f24 --> f7
    f32 --> f0
    f32 --> f5
    f32 --> f2
    f33 --> f1
    f33 --> f9
    f33 --> f24
    f34 --> f7
    f42 --> f3
```

## ENTRY_POINTS

### `src/codectx/cli.py`

```python
"""codectx CLI — typer entrypoint wiring the full pipeline."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from codectx.config.defaults import CACHE_DIR_NAME

from codectx import __version__

app = typer.Typer(
    name="codectx",
    help="Codebase context compiler for AI agents.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console(stderr=True)


@app.command()
def analyze(
    root: Path = typer.Argument(
        ".",
        help="Repository root directory to analyze.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    tokens: int = typer.Option(
        None,
        "--tokens",
        "-t",
        help="Token budget (default: 120000).",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: CONTEXT.md).",
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Include recent changes since this date (e.g. '7 days ago').",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging.",
    ),
    no_git: bool = typer.Option(
        False,
        "--no-git",
        help="Skip git metadata collection.",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Semantic query to rank files by relevance (requires codectx[semantic]).",
    ),
    extra_roots: Optional[list[Path]] = typer.Option(
        None,
        "--extra-root",
        help="Additional root directories for multi-root analysis.",
    ),
) -> None:
    """Analyze a codebase and generate CONTEXT.md."""
    _setup_logging(verbose)
    start_time = time.perf_counter()

    from codectx.config.loader import load_config

    # Build roots list: primary root + any extra roots
    roots_list: list[Path] | None = None
    if extra_roots:
        roots_list = [root] + list(extra_roots)

    config = load_config(
        root,
        token_budget=tokens,
        output_file=str(output) if output else None,
        since=since,
        verbose=verbose,
        no_git=no_git,
        query=query or "",
        roots=roots_list,
    )

    result_path = _run_pipeline(config)
    elapsed = time.perf_counter() - start_time

    console.print(
        Panel(
            f"[bold green]✓[/] Context written to [bold]{result_path}[/]\n  Time: {elapsed:.2f}s",
            title="codectx",
            border_style="green",
        )
    )


@app.command()
def benchmark(
    root: Path = typer.Argument(
        ".",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    tokens: int = typer.Option(None, "--tokens", "-t"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    no_git: bool = typer.Option(False, "--no-git"),
) -> None:
    """Run analysis with detailed timing and stats."""
    _setup_logging(verbose)

    from codectx.config.loader import load_config

    config = load_config(
        root,
        token_budget=tokens,
        verbose=verbose,
        no_git=no_git,
    )

    console.print("[bold]Running benchmark...[/]\n")

    timings: dict[str, float] = {}

    # Walk
    t0 = time.perf_counter()
    from codectx.walker import walk

    files = walk(config.root, config.extra_ignore)
    timings["walk"] = time.perf_counter() - t0

    # Parse
    t0 = time.perf_counter()
    from codectx.parser.treesitter import parse_files

    parse_results = parse_files(files)
    timings["parse"] = time.perf_counter() - t0

    # Graph
    t0 = time.perf_counter()
    from codectx.graph.builder import build_dependency_graph

    dep_graph = build_dependency_graph(parse_results, config.root)
    timings["graph"] = time.perf_counter() - t0

    # Rank
    t0 = time.perf_counter()
    from codectx.ranker.git_meta import collect_git_metadata, collect_recent_changes
    from codectx.ranker.scorer import score_files

    git_meta = collect_git_metadata(files, config.root, config.no_git)
    scores = score_files(files, dep_graph, git_meta)
    timings["rank"] = time.perf_counter() - t0

    # Compress
    t0 = time.perf_counter()
    from codectx.compressor.budget import TokenBudget
    from codectx.compressor.tiered import compress_files

    budget = TokenBudget(config.token_budget)
    compressed = compress_files(parse_results, scores, budget, config.root)
    timings["compress"] = time.perf_counter() - t0

    total = sum(timings.values())

    console.print(
        Panel(
            "\n".join(
                [
                    f"[bold]Files discovered:[/] {len(files)}",
                    f"[bold]Files parsed:[/] {len(parse_results)}",
                    f"[bold]Graph nodes:[/] {dep_graph.node_count}",
                    f"[bold]Graph edges:[/] {dep_graph.edge_count}",
                    f"[bold]Compressed files:[/] {len(compressed)}",
                    f"[bold]Tokens used:[/] {budget.used:,} / {budget.total:,}",
                    "",
                    *[f"  {k:>10}: {v:.3f}s" for k, v in timings.items()],
                    f"  {'total':>10}: {total:.3f}s",
                ]
            ),
            title="Benchmark Results",
            border_style="cyan",
        )
    )


@app.command()
def watch(
    root: Path = typer.Argument(
        ".",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    tokens: int = typer.Option(None, "--tokens", "-t"),
    output: Path = typer.Option(None, "--output", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    no_git: bool = typer.Option(False, "--no-git"),
) -> None:
    """Watch for file changes and regenerate CONTEXT.md."""
    _setup_logging(verbose)

    from codectx.config.loader import load_config

    config = load_config(
        root,
        token_budget=tokens,
        output_file=str(output) if output else None,
        verbose=verbose,
        no_git=no_git,
        watch=True,
    )

    console.print(f"[bold]Watching[/] {config.root} for changes...")
    console.print("Press Ctrl+C to stop.\n")

    # Initial run
    _run_pipeline(config)
    console.print("[green]Initial context generated.[/]\n")

    try:
        from watchfiles import watch as watchfiles_watch

        for changes in watchfiles_watch(str(config.root)):
            changed_paths = [Path(c[1]) for c in changes]
            console.print(f"[yellow]Changes detected:[/] {len(changed_paths)} file(s)")
            try:
                _run_pipeline(config)
                console.print("[green]Context regenerated.[/]\n")
            except Exception as exc:
                console.print(f"[red]Error during regeneration: {exc}[/]\n")
    except KeyboardInterrupt:
        console.print("\n[bold]Watch stopped.[/]")


# ---------------------------------------------------------------------------
# Cache commands
# ---------------------------------------------------------------------------

cache_app = typer.Typer(help="Manage the codectx cache.")
app.add_typer(cache_app, name="cache")


@cache_app.command("export")
def cache_export(
    root: Path = typer.Argument(
        ".",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        ".codectx_cache.tar.gz",
        "--output",
        "-o",
        help="Output archive path.",
    ),
) -> None:
    """Export the cache as a tar.gz archive for CI sharing."""
    from codectx.cache import Cache

    cache = Cache(root)
    try:
        cache.export_cache(output)
        console.print(f"[bold green]✓[/] Cache exported to [bold]{output}[/]")
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(1)


@cache_app.command("import")
def cache_import(
    root: Path = typer.Argument(
        ".",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    archive: Path = typer.Option(
        ".codectx_cache.tar.gz",
        "--input",
        "-i",
        help="Input archive path.",
    ),
) -> None:
    """Import a cache archive for CI sharing."""
    from codectx.cache import Cache

    try:
        Cache.import_cache(archive, root)
        console.print(f"[bold green]✓[/] Cache imported from [bold]{archive}[/]")
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
    ),
) -> None:
    """codectx — Codebase context compiler for AI agents."""
    if version:
        typer.echo(f"codectx {__version__}")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def _run_pipeline(config: "object") -> Path:
    """Run the full codectx pipeline and return the output file path."""
    import hashlib

    from codectx.cache import Cache
    from codectx.compressor.budget import TokenBudget
    from codectx.compressor.tiered import compress_files
    from codectx.config.loader import Config
    from codectx.graph.builder import build_dependency_graph
    from codectx.output.formatter import format_context, write_context_file
    from codectx.parser.treesitter import parse_file, parse_files
    from codectx.ranker.git_meta import collect_git_metadata, collect_recent_changes
    from codectx.ranker.scorer import score_files
    from codectx.safety import confirm_sensitive_files, find_sensitive_files
    from codectx.walker import walk, walk_multi

    assert isinstance(config, Config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        # Step 1: Walk (supports multi-root)
        task = progress.add_task("Discovering files...", total=None)

        if len(config.roots) > 1:
            files_by_root = walk_multi(
                config.roots, config.extra_ignore, output_file=config.output_file
            )
            files: list[Path] = []
            for root_files in files_by_root.values():
                files.extend(root_files)
        else:
            files = walk(config.root, config.extra_ignore, output_file=config.output_file)

        progress.update(task, description=f"Found {len(files)} files")

        # Step 1.5: Safety check
        sensitive = find_sensitive_files(files, config.root)
        if sensitive:
            progress.stop()
            if not confirm_sensitive_files(sensitive, config.root):
                # Remove sensitive files
                sensitive_set = set(sensitive)
                files = [f for f in files if f not in sensitive_set]
            progress.start()

        # Step 2: Parse (cache-aware)
        progress.update(task, description="Parsing files...")
        cache = Cache(config.root)

        parse_results = {}
        uncached_files: list[Path] = []

        for f in files:
            try:
                fhash = hashlib.sha256(f.read_bytes()).hexdigest()
            except OSError:
                fhash = ""

            cached = cache.get_parse_result(f, fhash)
            if cached is not None:
                parse_results[f] = cached
            else:
                uncached_files.append(f)

        # Batch-parse uncached files
        if uncached_files:
            fresh = parse_files(uncached_files)
            for f, result in fresh.items():
                parse_results[f] = result
                try:
                    fhash = hashlib.sha256(f.read_bytes()).hexdigest()
                except OSError:
                    fhash = ""
                cache.put_parse_result(f, fhash, result)

        # Step 3: Build dependency graph
        progress.update(task, description="Building dependency graph...")
        dep_graph = build_dependency_graph(parse_results, config.root)

        # Step 4: Collect git metadata + score
        progress.update(task, description="Scoring files...")
        git_meta = collect_git_metadata(files, config.root, config.no_git)
        recent_changes = collect_recent_changes(config.root, config.since, config.no_git)

        # Optional: semantic scoring via --query
        sem_scores: dict[Path, float] | None = None
        if config.query:
            try:
                from codectx.ranker.semantic import is_available, semantic_score

                if is_available():
                    progress.update(task, description="Computing semantic relevance...")
                    cache_dir = config.root / CACHE_DIR_NAME
                    cache_dir.mkdir(exist_ok=True)
                    sem_scores = semantic_score(config.query, files, parse_results, cache_dir)
            except Exception as exc:
                import logging

                logging.getLogger(__name__).debug("Semantic scoring skipped: %s", exc)

        scores = score_files(files, dep_graph, git_meta, semantic_scores=sem_scores)

        # Step 5: Compress
        progress.update(task, description="Compressing to token budget...")
        budget = TokenBudget(config.token_budget)
        compressed = compress_files(
            parse_results,
            scores,
            budget,
            config.root,
            llm_enabled=config.llm_enabled,
            llm_provider=config.llm_provider,
            llm_model=config.llm_model,
        )

        # Step 6: Format and write
        progress.update(task, description="Writing output...")

        # Load architecture text if available
        arch_text = ""
        arch_file = config.root / "ARCHITECTURE.md"
        if arch_file.is_file():
            arch_text = arch_file.read_text(encoding="utf-8", errors="replace")

        content = format_context(
            compressed=compressed,
            dep_graph=dep_graph,
            root=config.root,
            budget=budget,
            architecture_text=arch_text,
            recent_changes=recent_changes,
            roots=config.roots if len(config.roots) > 1 else None,
        )

        output_path = config.root / config.output_file
        write_context_file(content, output_path)

        # Step 7: Persist cache
        cache.save()

        progress.update(task, description="Done!")

    return output_path


def _setup_logging(verbose: bool) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(name)s: %(message)s",
        stream=sys.stderr,
    )

```

## CORE_MODULES

### `src/codectx/parser/base.py`

> Core data structures for the parser module.

```python
class Symbol
    """A top-level symbol extracted from a source file."""

class ParseResult
    """Result of parsing a single source file."""

def make_plaintext_result(path: Path, source: str) -> ParseResult
    """Create a minimal ParseResult for unsupported language files."""

```

### `src/codectx/walker.py`

> File-system walker — discovers files, applies ignore specs, filters binaries."""



```python
def lk(
(    root: Path,
    extra_ignore: tuple[str, ...] = (),
    output_file: Path | None = None,
) -) -> st[Path]:

    """"Recursively discover non-ignored, non-binary files under *root*.

    Args:
        root: Repository root directory.
        extra_ignore: Additional ignore patterns from config.
        output_file: Output file to exclude from results (prevents self-inclusion).

    Returns:
        Sorted list of absolute file paths.
    """"""

def ollect(
(    current: Path,
    root: Path,
    spec: "object",  # pathspec.PathSpec
    out: list[Path],
) -) -> ne:

    """"Recursively collect files, pruning ignored directories.""""""

def s_binary(p(ath: Path) -) -> ol:

    """"Detect binary files by probing UTF-8 decoding on the initial byte chunk.""""""

def lk_multi(
(    roots: list[Path],
    extra_ignore: tuple[str, ...] = (),
    output_file: Path | None = None,
) -) -> ct[Path, list[Path]]:

    """"Walk multiple roots independently, returning files grouped by root.

    Args:
        roots: List of repository root directories.
        extra_ignore: Additional ignore patterns from config.
        output_file: Output file to exclude from results.

    Returns:
        Dict mapping each root to sorted list of absolute file paths.
    """"""

def nd_root(f(ile_path: Path, roots: list[Path]) -) -> th | None:

    """"Determine which root a file belongs to.

    Args:
        file_path: Absolute path to a file.
        roots: List of root directories.

    Returns:
        The root the file belongs to, or None if not under any root.
    """"""

```

### `src/codectx/parser/treesitter.py`

> Tree-sitter AST extraction — parallel parsing of source files."""



```python
def arse_scm_patterns(t(ext: str) -) -> st[tuple[str, str]]:

    """"Parse S-expression (.scm) text into (node_type, capture_name) pairs.

    Handles nested parentheses like:
        (function_definition name: (identifier) @name) @function
    Returns the *outermost* node_type with its trailing @capture.
    """"""

class erySpec:

    """"Parsed query specification from a .scm file.""""""

def oad_query_spec(l(anguage: str) -) -> erySpec | None:

    """"Load and parse a .scm query file for the given language.""""""

def et_query_spec(l(anguage: str) -) -> erySpec | None:

    """"Get cached QuerySpec for a language.""""""

def rse_files(f(iles: list[Path]) -) -> ct[Path, ParseResult]:

    """"Parse multiple files in parallel using ProcessPoolExecutor.

    Files with unsupported languages get a plain-text ParseResult.
    """"""

def rse_file(p(ath: Path) -) -> rseResult:

    """"Parse a single file (synchronous, for caching or single-file use).""""""

def arse_single_worker(a(rgs: tuple[str, str, str]) -) -> rseResult:

    """"Worker function for ProcessPoolExecutor. Receives serializable args.""""""

def xtract(p(ath: Path, source: str, entry: LanguageEntry) -) -> rseResult:

    """"Extract imports, symbols, and docstrings from source via tree-sitter.""""""

def allback_parse(p(ath: Path, source: str, language: str) -) -> rseResult:

    """"Best-effort fallback extraction when tree-sitter parsing fails.""""""

def egex_imports(s(ource: str, language: str) -) -> st[str]:

    """"Extract import-like lines via lightweight regex patterns.""""""

def egex_docstrings(s(ource: str, language: str) -) -> st[str]:

    """"Extract a module-level docstring/comment for fallback parsing.""""""

def xtract_imports(n(ode: Any, language: str, source: str) -) -> st[str]:

    """"Extract import strings from the AST.

    Uses .scm query spec (data-driven) if available, otherwise falls back
    to manual per-language logic for c, cpp, ruby.
    """"""

def xtract_symbols(n(ode: Any, language: str, source: str) -) -> st[Symbol]:

    """"Extract top-level functions and classes.""""""

def xtract_module_docstrings(n(ode: Any, language: str, source: str) -) -> st[str]:

    """"Extract module-level docstrings.""""""

def ython_func_symbol(n(ode: Any, source: str, kind: str) -) -> mbol:


def ython_class_symbol(n(ode: Any, source: str) -) -> mbol:


def s_func_symbol(n(ode: Any, source: str) -) -> mbol:


def s_class_symbol(n(ode: Any, source: str) -) -> mbol:


def aybe_js_arrow(n(ode: Any, source: str, symbols: list[Symbol]) -) -> ne:

    """"Handle `const foo = () => {}` pattern.""""""

def o_func_symbol(n(ode: Any, source: str, kind: str = "function") -) -> mbol:


def eneric_symbol(n(ode: Any, source: str, kind: str) -) -> mbol:

    """"Generic symbol extractor — takes first identifier as name.""""""

def k_tree(nod(e: Any) -> ) -> [Any]:
  
    """terate over all nodes in the tree (BFS).""""""

def e_text(nod(e: Any, source: str) -> ) -> 
  
    """et the source text for a tree-sitter node.""""""

def d_child(nod(e: Any, child_type: str) -> ) -> | None:
  
    """ind first child of a given type.""""""

def ract_first_docstring(bod(y_node: Any, source: str) -> ) -> 
  
    """xtract docstring from the first expression_statement in a body block.""""""

def d_source(pat(h: Path) -> ) -> 
  
    """ead a source file as UTF-8 text.""""""

```

### `src/codectx/cache.py`

> File-level caching for parse results, token counts, and git metadata.

```python
class Cache
    """JSON-based file cache in .codectx_cache/."""

def file_hash(path: Path) -> str
    """Compute a fast hash of file contents."""

```

### `src/codectx/config/loader.py`

> Configuration loader — reads .codectx.toml or pyproject.toml [tool.codectx]."""



```python
class nfig:

    """"Resolved configuration for a codectx run.""""""

def ad_config(r(oot: Path, **cli_overrides: object) -) -> nfig:

    """"Load config from .codectx.toml → pyproject.toml [tool.codectx] → defaults.

    CLI overrides take highest precedence.
    """
    f"""

def ve(
    (key: str,
    cli: dict[str, object],
    file_cfg: dict[str, object],
    default: object,
) -> ob) -> :
    
    """olve a config key with precedence: CLI > file > default."""
    c"""

```

### `src/codectx/graph/builder.py`

> Dependency graph construction using rustworkx.

```python
class DepGraph
    """Dependency graph with file-level nodes and import edges."""

def build_dependency_graph(
    parse_results: dict[Path, ParseResult],
    root: Path,
) -> DepGraph
    """Build a dependency graph from parse results.

    Args:
        parse_results: Mapping of file paths to their parse results.
        root: Repository root directory.

    Returns:
        Constructed DepGraph."""

```

### `src/codectx/config/defaults.py`

> Default configuration values and constants for codectx.

*136 lines, 1 imports*

### `src/codectx/output/formatter.py`

> Structured markdown formatter — emits CONTEXT.md."""



```python
def oot_label(f(ile_path: Path, roots: list[Path] | None) -) -> r:

    """"Return a root label prefix if multi-root, else empty string.""""""

def rmat_context(
(    compressed: list[CompressedFile],
    dep_graph: DepGraph,
    root: Path,
    budget: TokenBudget,
    architecture_text: str = "",
    recent_changes: str = "",
    roots: list[Path] | None = None,
) -) -> r:

    """"Assemble the full CONTEXT.md content.

    Sections are emitted in the canonical order and consume the token budget.
    """"""

def ite_context_file(c(ontent: str, output_path: Path) -) -> ne:

    """"Write the assembled context to disk.""""""

def ection_header(t(itle: str) -) -> r:


def uto_architecture(c(ompressed: list[CompressedFile], root: Path) -) -> r:

    """"Generate a simple architecture summary from the file list.""""""

def ender_mermaid_graph(
(    dep_graph: DepGraph,
    root: Path,
    compressed: list[CompressedFile],
) -) -> r:

    """"Render the dependency graph as a Mermaid diagram.

    Limited to top N ranked modules to keep the diagram readable.
    """"""

```

### `src/codectx/compressor/tiered.py`

> Tiered compression — assigns tiers and enforces token budget."""



```python
class mpressedFile:

    """"A file compressed to its assigned tier.""""""

def sign_tiers(
(    scores: dict[Path, float],
) -) -> ct[Path, int]:

    """"Assign tier to each file based on its score.

    Tier 1 (score > 0.7): full source
    Tier 2 (0.3–0.7): signatures + docstrings
    Tier 3 (< 0.3): one-line summary
    """"""

def ress_files(
  (  parse_results: dict[Path, ParseResult],
    scores: dict[Path, float],
    budget: TokenBudget,
    root: Path,
    llm_enabled: bool = False,
    llm_provider: str = "openai",
    llm_model: str = "",
) -> ) -> [CompressedFile]:
  
    """Compress files into tiered content within the token budget.

    Budget consumption order:
      1. Tier 1 files (full source), by score descending
      2. Tier 2 files (signatures + docstrings), by score descending
      3. Tier 3 files (one-line summary), by score descending

    Overflow policy: drop Tier 3 → truncate Tier 2 → truncate Tier 1.
    """
    tie"""

def arseResult, pa(th: Path, root: Path) -> str:
    """Tier) -> ful
    """ce with metadata header."""
    rel = path.rela"""

def arseResult, pa(th: Path, root: Path) -> str:
    """Tier) -> fun
    """class signatures + docstrings."""
    rel = path.rela"""

def arseResult, pa(th: Path, root: Path) -> str:
    """Tier) -> one
    """summary."""
    rel = path.rela"""

def ParseResult) -> s(tr:
    """Genera) ->  on
    """summary from parse result."""
    parts: list[str]"""

```

### `src/codectx/ranker/git_meta.py`

> Git metadata extraction via pygit2.

```python
class GitFileInfo
    """Git metadata for a single file."""

def collect_git_metadata(
    files: list[Path],
    root: Path,
    no_git: bool = False,
    max_commits: int = 5000,
) -> dict[Path, GitFileInfo]
    """Collect git metadata for all files.

    Args:
        files: List of absolute file paths.
        root: Repository root.
        no_git: If True, use filesystem metadata only.
        max_commits: Max number of commits to walk (default: 5000).

    Returns:
        Mapping of file path to GitFileInfo."""

def _collect_from_git(
    repo: object,  # pygit2.Repository
    files: list[Path],
    root: Path,
    max_commits: int,
) -> dict[Path, GitFileInfo]
    """Walk git log to collect per-file commit counts and last-modified times."""

def ilesystem_fallback(f(iles: list[Path]) -) -> ct[Path, GitFileInfo]:

    """"Fallback using filesystem metadata when git is unavailable.""""""

def llect_recent_changes(r(oot: Path, since: str | None, no_git: bool = False) -) -> r:

    """"Collect a deterministic markdown summary of recent git changes.""""""

def arse_since(s(ince: str) -) -> oat | None:

    """"Parse --since values like '7 days ago' or ISO date strings.""""""

```

### `src/codectx/graph/resolver.py`

> Per-language import string → file path resolution."""



```python
def solve_import(
(    import_text: str,
    language: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -) -> st[Path]:

    """"Resolve an import statement to file paths within the repository.

    Args:
        import_text: Raw import string from the AST.
        language: Language name (e.g. "python").
        source_file: Absolute path of the file containing the import.
        root: Repository root.
        all_files: Set of all known file paths (POSIX, relative to root).

    Returns:
        List of resolved file paths (may be empty if unresolvable).
    """"""

def solve_import_multi_root(
(    import_text: str,
    language: str,
    source_file: Path,
    roots: list[Path],
    all_files_by_root: dict[Path, frozenset[str]],
) -) -> st[Path]:

    """"Resolve an import trying the source file's root first, then others.

    Args:
        import_text: Raw import string from the AST.
        language: Language name.
        source_file: Absolute path of the file containing the import.
        roots: All root directories.
        all_files_by_root: Map of root → set of relative file paths.

    Returns:
        List of resolved file paths.
    """"""

def olve_python(
  (  import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> ) -> [Path]:
  

def olve_js_ts(
  (  import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> ) -> [Path]:
  

def olve_go(imp(ort_text: str, root: Path, all_files: frozenset[str]) -> ) -> [Path]:
  

def olve_rust(
  (  import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> ) -> [Path]:
  

def ve_java(impor(t_text: str, root: Path, all_files: frozenset[str]) -> li) -> ath]:
    

def ve_c_cpp(
    (import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> li) -> ath]:
    

def ve_ruby(
    (import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> li) -> ath]:
    

```

### `tests/test_walker.py`

> Tests for the file walker.

```python
def temp_repo(tmp_path: Path) -> Path
    """Create a temporary repo with various files."""

def test_walk_finds_source_files(temp_repo: Path) -> None
    """Walker should find regular source files."""

def test_walk_skips_ignored_dirs(temp_repo: Path) -> None
    """Walker should skip __pycache__ and node_modules."""

def test_walk_skips_binary_files(temp_repo: Path) -> None
    """Walker should filter out binary files."""

def test_walk_skips_invalid_utf8_binary(temp_repo: Path) -> None
    """Files that fail UTF-8 decoding should be treated as binary."""

def test_walk_returns_sorted(temp_repo: Path) -> None
    """Result should be sorted by path."""

def test_walk_returns_absolute_paths(temp_repo: Path) -> None
    """All returned paths should be absolute."""

```

### `tests/test_parser.py`

> Tests for tree-sitter parsing.

```python
def python_file(tmp_path: Path) -> Path
    """Create a Python file with known structure."""

def test_parse_python_language(python_file: Path) -> None
    """Parser should detect Python language."""

def test_parse_python_imports(python_file: Path) -> None
    """Parser should extract import statements."""

def test_parse_python_functions(python_file: Path) -> None
    """Parser should extract function symbols."""

def test_parse_python_classes(python_file: Path) -> None
    """Parser should extract class symbols."""

def test_parse_python_docstrings(python_file: Path) -> None
    """Parser should extract module-level docstrings."""

def test_parse_python_function_docstring(python_file: Path) -> None
    """Parser should extract function docstrings."""

def test_parse_unsupported_file(tmp_path: Path) -> None
    """Unsupported file extensions should get a plain-text result."""

def test_parse_line_count(python_file: Path) -> None
    """ParseResult should have accurate line count."""

def test_parse_raw_source(python_file: Path) -> None
    """ParseResult should contain the original source."""

def test_parse_supported_file_not_partial(python_file: Path) -> None
    """Successful tree-sitter parse should not be marked partial."""

def test_parse_fallback_marks_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None
    """When tree-sitter fails, parser should return a partial parse result."""

```

## PERIPHERY

- `pyproject.toml` — 90 lines
- `src/codectx/ranker/semantic.py` — Semantic search ranking using lancedb and sentence-transformers.
- `src/codectx/ranker/scorer.py` — Composite file scoring — ranks files by importance."""
- `tests/unit/test_cache_export.py` — Tests for CI cache export/import.
- `tests/unit/test_cache_wiring.py` — Tests for cache wiring into the analyze pipeline.
- `tests/unit/test_semantic.py` — Tests for semantic search ranking module.
- `tests/unit/test_formatter_sections.py` — Tests for deterministic formatter section ordering and presence.
- `tests/test_scorer.py` — Tests for the composite file scorer.
- `tests/unit/test_cycles.py` — Tests for cyclic dependency detection.
- `tests/unit/test_summarizer.py` — Tests for LLM summarizer module.
- `src/codectx/compressor/budget.py` — Token counting and budget tracking via tiktoken.
- `requirements.txt` — 113 lines
- `src/codectx/parser/languages.py` — Extension → language mapping for tree-sitter parsers."""
- `tests/test_integration.py` — Integration test — runs codectx pipeline end-to-end."""
- `.gitignore` — 18 lines
- `main.py` — 1 function, 7 lines
- `src/codectx/compressor/summarizer.py` — LLM-based file summarization for Tier 3 compression.
- `src/codectx/ignore.py` — Ignore-spec handling — layers ALWAYS_IGNORE, .gitignore, .ctxignore."""
- `tests/unit/test_multi_root.py` — Tests for multi-root support.
- `tests/test_compressor.py` — Tests for tiered compression and token budget.
- `src/codectx/safety.py` — Sensitive-file detection and user confirmation.
- `src/codectx/parser/queries/go.scm` — 7 lines
- `src/codectx/parser/queries/java.scm` — 5 lines
- `src/codectx/parser/queries/javascript.scm` — 8 lines
- `src/codectx/parser/queries/python.scm` — 7 lines
- `src/codectx/parser/queries/rust.scm` — 8 lines
- `src/codectx/parser/queries/typescript.scm` — 8 lines
- `tests/unit/__init__.py` — 0 lines
- `tests/unit/test_queries.py` — Tests for .scm query file loading and data-driven extraction.
- `src/codectx/__init__.py` — codectx — Codebase context compiler for AI agents."""
- `src/codectx/compressor/__init__.py` — 0 lines
- `src/codectx/config/__init__.py` — 0 lines
- `src/codectx/graph/__init__.py` — 0 lines
- `src/codectx/output/__init__.py` — 0 lines
- `src/codectx/output/sections.py` — Section constants for CONTEXT.md output.
- `src/codectx/parser/__init__.py` — 0 lines
- `src/codectx/ranker/__init__.py` — 0 lines
- `tests/__init__.py` — 0 lines
- `tests/test_ignore.py` — Tests for ignore-spec handling.
- `.python-version` — 2 lines
- `ARCHITECTURE.md` — 113 lines
- `CLAUDE.md` — 91 lines
- `DECISIONS.md` — 82 lines
- `PLAN.md` — 54 lines
- `README.md` — 0 lines

## RECENT_CHANGES

*No recent changes included.*

