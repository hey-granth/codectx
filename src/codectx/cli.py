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
            f"[bold green]✓[/] Context written to [bold]{result_path}[/]\n"
            f"  Time: {elapsed:.2f}s",
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

    console.print(Panel(
        "\n".join([
            f"[bold]Files discovered:[/] {len(files)}",
            f"[bold]Files parsed:[/] {len(parse_results)}",
            f"[bold]Graph nodes:[/] {dep_graph.node_count}",
            f"[bold]Graph edges:[/] {dep_graph.edge_count}",
            f"[bold]Compressed files:[/] {len(compressed)}",
            f"[bold]Tokens used:[/] {budget.used:,} / {budget.total:,}",
            "",
            *[f"  {k:>10}: {v:.3f}s" for k, v in timings.items()],
            f"  {'total':>10}: {total:.3f}s",
        ]),
        title="Benchmark Results",
        border_style="cyan",
    ))


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
        console.print(
            f"[bold green]✓[/] Cache exported to [bold]{output}[/]"
        )
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
        console.print(
            f"[bold green]✓[/] Cache imported from [bold]{archive}[/]"
        )
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
    from codectx.ranker.git_meta import collect_git_metadata
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

        # Optional: semantic scoring via --query
        sem_scores: dict[Path, float] | None = None
        if config.query:
            try:
                from codectx.ranker.semantic import is_available, semantic_score

                if is_available():
                    progress.update(task, description="Computing semantic relevance...")
                    cache_dir = config.root / CACHE_DIR_NAME
                    cache_dir.mkdir(exist_ok=True)
                    sem_scores = semantic_score(
                        config.query, files, parse_results, cache_dir
                    )
            except Exception as exc:
                import logging
                logging.getLogger(__name__).debug(
                    "Semantic scoring skipped: %s", exc
                )

        scores = score_files(files, dep_graph, git_meta, semantic_scores=sem_scores)

        # Step 5: Compress
        progress.update(task, description="Compressing to token budget...")
        budget = TokenBudget(config.token_budget)
        compressed = compress_files(
            parse_results, scores, budget, config.root,
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
