"""codectx CLI — typer entrypoint wiring the full pipeline."""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from codectx import __version__
from codectx.config.defaults import CACHE_DIR_NAME

if TYPE_CHECKING:
    from codectx.output.formatter import CompressionResult

try:
    from codectx.llm import llm_dependencies_available

    _LLM_AVAILABLE = llm_dependencies_available()
except Exception:
    _LLM_AVAILABLE = False


_WATCH_SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".go",
        ".rs",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".rb",
        ".php",
    }
)
_WATCH_IGNORED_DIRS: frozenset[str] = frozenset(
    {"__pycache__", ".git", "node_modules", "dist", "build"}
)
_WATCH_IGNORED_NAMES: frozenset[str] = frozenset({"package-lock.json", "yarn.lock", "uv.lock"})
_WATCH_IGNORED_GLOBS: tuple[str, ...] = ("*.pyc", "*.pyo", "*.lock")


def _watch_path_is_relevant(path: Path) -> bool:
    parts = set(path.parts)
    if parts.intersection(_WATCH_IGNORED_DIRS):
        return False
    if path.name in _WATCH_IGNORED_NAMES:
        return False
    if any(fnmatch(path.name, pattern) for pattern in _WATCH_IGNORED_GLOBS):
        return False
    return path.suffix.lower() in _WATCH_SOURCE_EXTENSIONS


class DebouncedHandler:
    def __init__(self, delay: float, callback: Callable[[set[str]], None]) -> None:
        self._delay = delay
        self._callback = callback
        self._timer: threading.Timer | None = None
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    def on_any_event(self, event: Any) -> None:
        if bool(getattr(event, "is_directory", False)):
            return
        src_path = str(getattr(event, "src_path", ""))
        if not src_path:
            return
        with self._lock:
            self._pending.add(src_path)
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._fire)
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            paths = self._pending.copy()
            self._pending.clear()
        callback = self._callback
        if callable(callback):
            callback(paths)


app = typer.Typer(
    name="codectx",
    help="Codebase context compiler for AI agents.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console(stderr=True)


@app.command()
def analyze(
    root: Path = typer.Argument(  # noqa: B008
        ".",
        help="Repository root directory to analyze.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    tokens: int = typer.Option(  # noqa: B008
        None,
        "--tokens",
        "-t",
        help="Token budget (default: 120000).",
    ),
    output: Path = typer.Option(  # noqa: B008
        None,
        "--output",
        "-o",
        help="Output file path (default: CONTEXT.md).",
    ),
    since: str | None = typer.Option(  # noqa: B008
        None,
        "--since",
        help="Include recent changes since this date (e.g. '7 days ago').",
    ),
    verbose: bool = typer.Option(  # noqa: B008
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging.",
    ),
    no_git: bool = typer.Option(  # noqa: B008
        False,
        "--no-git",
        help="Skip git metadata collection.",
    ),
    query: str | None = typer.Option(  # noqa: B008
        None,
        "--query",
        "-q",
        help="Semantic query to rank files by relevance (requires codectx[semantic]).",
    ),
    task: str = typer.Option(  # noqa: B008
        "default",
        "--task",
        help="Task profile for context generation (debug, feature, architecture, default).",
    ),
    layers: bool = typer.Option(  # noqa: B008
        False,
        "--layers",
        help="Generate layered context output.",
    ),
    extra_roots: list[Path] | None = typer.Option(  # noqa: B008
        None,
        "--extra-root",
        help="Additional root directories for multi-root analysis.",
    ),
    output_format: str = typer.Option(
        "markdown", "--format", help="Output format: markdown or json."
    ),  # noqa: B008
    llm: bool = typer.Option(False, "--llm/--no-llm", help="Enable LLM-powered summaries."),  # noqa: B008
    llm_provider: str = typer.Option("openai", "--llm-provider", help="LLM provider."),  # noqa: B008
    llm_model: str = typer.Option("", "--llm-model", help="LLM model name."),  # noqa: B008
    llm_api_key: str | None = typer.Option(None, "--llm-api-key", help="LLM API key override."),  # noqa: B008
    llm_base_url: str | None = typer.Option(None, "--llm-base-url", help="LLM base URL override."),  # noqa: B008
    llm_max_tokens: int = typer.Option(256, "--llm-max-tokens", help="Max tokens per LLM summary."),  # noqa: B008
) -> None:
    """Analyze a codebase and generate CONTEXT.md."""
    _setup_logging(verbose)
    start_time = time.perf_counter()

    from codectx.config.loader import load_config

    # Build roots list: primary root + any extra roots
    roots_list: list[Path] | None = None
    if extra_roots:
        roots_list = [root] + list(extra_roots)

    if output_format not in {"markdown", "json"}:
        raise typer.BadParameter("--format must be one of: markdown, json")

    if llm and not _LLM_AVAILABLE:
        import click

        raise click.UsageError("LLM dependencies missing. Install with: pip install codectx[llm]")

    config = load_config(
        root,
        token_budget=tokens,
        output_file=str(output) if output else None,
        since=since,
        verbose=verbose,
        no_git=no_git,
        query=query or "",
        task=task,
        layers=layers,
        roots=roots_list,
        output_format=output_format,
        llm_enabled=llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        llm_max_tokens=llm_max_tokens,
    )

    metrics = _run_pipeline(config, quiet=output_format == "json")
    elapsed = time.perf_counter() - start_time

    ratio = metrics.original_tokens / metrics.context_tokens if metrics.context_tokens > 0 else 0

    if output_format == "json":
        from codectx.output.formatter import format_json

        if metrics.compression_result is None:
            raise typer.Exit(1)
        typer.echo(format_json(metrics.compression_result))
        return

    console.print(
        Panel(
            f"[bold green]✓[/] Context written to [bold]{metrics.output_path}[/]\n\n"
            f"[bold]Files scanned:[/] {metrics.files_scanned:,}\n"
            f"[bold]Source tokens (excl. tests/docs):[/] {metrics.original_tokens:,}\n"
            f"[bold]Context tokens:[/] {metrics.context_tokens:,}\n"
            f"[bold]Compression ratio:[/] {ratio:.1f}x\n"
            f"[bold]Analysis time:[/] {elapsed:.1f}s",
            title="codectx",
            border_style="green",
        )
    )


@app.command()
def benchmark(
    root: Path = typer.Argument(  # noqa: B008
        ".",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    tokens: int = typer.Option(None, "--tokens", "-t"),  # noqa: B008
    verbose: bool = typer.Option(False, "--verbose", "-v"),  # noqa: B008
    no_git: bool = typer.Option(False, "--no-git"),  # noqa: B008
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
    from codectx.ranker.git_meta import collect_git_metadata
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
    root: Path = typer.Argument(  # noqa: B008
        ".",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    tokens: int = typer.Option(None, "--tokens", "-t"),  # noqa: B008
    output: Path = typer.Option(None, "--output", "-o"),  # noqa: B008
    verbose: bool = typer.Option(False, "--verbose", "-v"),  # noqa: B008
    no_git: bool = typer.Option(False, "--no-git"),  # noqa: B008
    debounce: float = typer.Option(3.0, "--debounce", help="Debounce delay in seconds."),  # noqa: B008
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
        debounce=debounce,
    )

    console.print(f"[bold]Watching[/] {config.root} for changes...")
    console.print("Press Ctrl+C to stop.\n")

    # Initial run
    _run_pipeline(config)
    console.print("[green]Initial context generated.[/]\n")

    try:
        import importlib

        watchdog_observers = importlib.import_module("watchdog.observers")
        Observer = watchdog_observers.Observer
    except Exception:
        # Keep compatibility with environments where watchdog is unavailable.
        from watchfiles import watch as watchfiles_watch

        try:
            for changes in watchfiles_watch(str(config.root)):
                changed_paths = [Path(c[1]) for c in changes]
                relevant = [p for p in changed_paths if _watch_path_is_relevant(p)]
                if not relevant:
                    continue
                console.print(f"[yellow]Changes detected:[/] {len(relevant)} source file(s)")
                _run_pipeline(config)
                console.print("[green]Context regenerated.[/]\n")
        except KeyboardInterrupt:
            console.print("\n[bold]Watch stopped.[/]")
        return

    observer = Observer()

    def _on_batch(paths: set[str]) -> None:
        changed_paths = [Path(p) for p in sorted(paths)]
        relevant = [p for p in changed_paths if _watch_path_is_relevant(p)]
        if not relevant:
            return
        console.print(f"[yellow]Changes detected:[/] {len(relevant)} source file(s)")
        try:
            _run_pipeline(config)
            console.print("[green]Context regenerated.[/]\n")
        except Exception as exc:
            console.print(f"[red]Error during regeneration: {exc}[/]\n")

    debounced = DebouncedHandler(float(config.debounce), _on_batch)

    observer.schedule(debounced, str(config.root), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        observer.stop()
        observer.join(timeout=2.0)
        console.print("\n[bold]Watch stopped.[/]")


@app.command()
def search(
    query: str = typer.Argument(  # noqa: B008
        ...,
        help="Semantic search query.",
    ),
    root: Path = typer.Option(  # noqa: B008
        ".",
        "--root",
        "-r",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    limit: int = typer.Option(  # noqa: B008
        10,
        "--limit",
        "-l",
        help="Number of results to return.",
    ),
    verbose: bool = typer.Option(  # noqa: B008
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging.",
    ),
) -> None:
    """Search the codebase semantically."""
    _setup_logging(verbose)

    try:
        from codectx.ranker.semantic import is_available, semantic_score

        if not is_available():
            console.print(
                "[red]Semantic search is not installed. Run: pip install codectx[semantic][/]"
            )
            raise typer.Exit(1)

        import hashlib

        from codectx.cache import Cache
        from codectx.config.loader import load_config
        from codectx.parser.base import ParseResult
        from codectx.parser.treesitter import parse_files
        from codectx.walker import walk

        config = load_config(root)
        files = walk(config.root, config.extra_ignore)

        # Parse files with cache
        cache = Cache(config.root)
        parse_results: dict[Path, ParseResult] = {}
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

        if uncached_files:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task("Parsing uncached files...", total=None)
                fresh = parse_files(uncached_files)
                for f, result in fresh.items():
                    parse_results[f] = result
                    try:
                        fhash = hashlib.sha256(f.read_bytes()).hexdigest()
                    except OSError:
                        fhash = ""
                    cache.put_parse_result(f, fhash, result)
            cache.save()

        cache_dir = config.root / ".codectx_cache" / "embeddings"
        cache_dir.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
        ) as progress:
            progress.add_task("Computing semantic relevance...", total=None)
            scores = semantic_score(query, files, parse_results, cache_dir)

        sorted_files = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        console.print(f"\n[bold cyan]Search Results for:[/] '{query}'\n")

        found = False
        for f, score in sorted_files[:limit]:
            if score > 0.0:
                rel = f.relative_to(config.root)
                console.print(f"[bold green]{rel}[/] (score: {score:.3f})")
                found = True

        if not found:
            console.print("[yellow]No relevant files found.[/]")

    except Exception as exc:
        console.print(f"[red]Error during search:[/] {exc}")
        raise typer.Exit(1) from exc


# ---------------------------------------------------------------------------
# Cache commands
# ---------------------------------------------------------------------------

cache_app = typer.Typer(help="Manage the codectx cache.")
app.add_typer(cache_app, name="cache")


@cache_app.command("export")
def cache_export(
    root: Path = typer.Argument(  # noqa: B008
        ".",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    output: Path = typer.Option(  # noqa: B008
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
        raise typer.Exit(1) from exc


@cache_app.command("import")
def cache_import(
    root: Path = typer.Argument(  # noqa: B008
        ".",
        help="Repository root directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    archive: Path = typer.Option(  # noqa: B008
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
        raise typer.Exit(1) from exc


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


@dataclass
class PipelineMetrics:
    output_path: Path
    files_scanned: int
    original_tokens: int
    context_tokens: int
    compression_result: CompressionResult | None = None


def _run_pipeline(config: object, quiet: bool = False) -> PipelineMetrics:
    """Run the full codectx pipeline and return the output metrics."""
    import hashlib

    from codectx.cache import Cache
    from codectx.compressor.budget import TokenBudget, count_tokens
    from codectx.compressor.tiered import compress_files
    from codectx.config.loader import Config
    from codectx.graph.builder import build_dependency_graph
    from codectx.output.formatter import (
        build_compression_result,
        format_context,
        write_context_file,
    )
    from codectx.parser.base import ParseResult
    from codectx.parser.treesitter import parse_files
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
        disable=quiet,
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

        parse_results: dict[Path, ParseResult] = {}
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
        _ = collect_recent_changes(config.root, config.since, config.no_git)

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

        scores = score_files(
            files,
            dep_graph,
            git_meta,
            semantic_scores=sem_scores,
            task=config.task,
            parse_results=parse_results,
        )

        # Step 5: Compress
        progress.update(task, description="Compressing to token budget...")
        budget = TokenBudget(config.token_budget)

        imported_by_map: dict[Path, set[str]] = {}
        for target_path, idx in dep_graph.path_to_idx.items():
            imported_by_map[target_path] = {
                dep_graph.idx_to_path[pred].as_posix()
                for pred in dep_graph.graph.predecessor_indices(idx)
                if pred in dep_graph.idx_to_path
            }

        compressed = compress_files(
            parse_results,
            scores,
            budget,
            config.root,
            imported_by_map=imported_by_map,
            llm_enabled=False,
        )

        if config.llm_enabled:
            from codectx.config.defaults import ENTRYPOINT_FILENAMES
            from codectx.llm import llm_summarize_sync

            llm_updated = []
            for cf in compressed:
                if cf.tier != 1 or cf.path.name in ENTRYPOINT_FILENAMES:
                    llm_updated.append(cf)
                    continue

                parsed = parse_results.get(cf.path)
                source = parsed.raw_source if parsed is not None else ""
                summary = llm_summarize_sync(
                    file_path=cf.path.relative_to(config.root).as_posix(),
                    file_content=source,
                    provider=config.llm_provider,
                    model=config.llm_model,
                    api_key=config.llm_api_key,
                    base_url=config.llm_base_url,
                    max_tokens=config.llm_max_tokens,
                )

                if summary:
                    new_content = (
                        f"### `{cf.path.relative_to(config.root).as_posix()}`\n\n{summary}\n"
                    )
                    llm_updated.append(
                        type(cf)(
                            path=cf.path,
                            tier=cf.tier,
                            score=cf.score,
                            content=new_content,
                            token_count=count_tokens(new_content),
                            language=cf.language,
                        )
                    )
                else:
                    llm_updated.append(cf)
            compressed = llm_updated

        # Step 6: Format and write
        progress.update(task, description="Writing output...")

        # Load architecture text if available
        arch_text = ""
        arch_file = config.root / "ARCHITECTURE.md"
        if arch_file.is_file():
            arch_text = arch_file.read_text(encoding="utf-8", errors="replace")

        content_sections = format_context(
            compressed=compressed,
            dep_graph=dep_graph,
            root=config.root,
            architecture_text=arch_text,
            roots=config.roots if len(config.roots) > 1 else None,
            parse_results=parse_results,
        )

        if config.output_format == "json":
            output_path = config.root / config.output_file
        elif config.layers:
            from codectx.output.formatter import write_layer_files

            write_layer_files(content_sections, config.root)
            output_path = config.root / "FULL_CONTEXT.md"
            write_context_file(content_sections, output_path)
        else:
            output_path = config.root / config.output_file
            write_context_file(content_sections, output_path)

        # Step 7: Persist cache
        cache.save()

        progress.update(task, description="Done!")

    original_tokens = sum(count_tokens(pr.raw_source) for pr in parse_results.values())

    compression_result = build_compression_result(
        compressed=compressed,
        root=config.root,
        budget_tokens=config.token_budget,
        parse_results=parse_results,
        version=os.environ.get("CODECTX_OUTPUT_VERSION", "0.3.0"),
    )

    return PipelineMetrics(
        output_path=output_path,
        files_scanned=len(files),
        original_tokens=original_tokens,
        context_tokens=sum(cf.token_count for cf in compressed),
        compression_result=compression_result,
    )


def _setup_logging(verbose: bool) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(name)s: %(message)s",
        stream=sys.stderr,
    )
