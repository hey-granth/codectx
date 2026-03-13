"""Structured markdown formatter — emits CONTEXT.md."""

from __future__ import annotations

from pathlib import Path

from codectx.compressor.budget import TokenBudget
from codectx.compressor.tiered import CompressedFile
from codectx.config.defaults import ENTRYPOINT_FILENAMES, MAX_MERMAID_NODES
from codectx.graph.builder import DepGraph
from codectx.output.sections import (
    ARCHITECTURE,
    CORE_MODULES,
    DEPENDENCY_GRAPH,
    ENTRY_POINTS,
    IMPORTANT_CALL_PATHS,
    PERIPHERY,
    SUPPORTING_MODULES,
    SYMBOL_INDEX,
)
from codectx.parser.base import ParseResult


def _root_label(file_path: Path, roots: list[Path] | None) -> str:
    """Return a root label prefix if multi-root, else empty string."""
    if not roots or len(roots) <= 1:
        return ""
    for r in roots:
        try:
            file_path.relative_to(r)
            return f"[{r.name}] "
        except ValueError:
            continue
    return ""


def format_context(
    compressed: list[CompressedFile],
    dep_graph: DepGraph,
    root: Path,
    budget: TokenBudget,
    architecture_text: str = "",
    roots: list[Path] | None = None,
    parse_results: dict[Path, ParseResult] | None = None,
) -> dict[str, str]:
    """Assemble the full CONTEXT.md content.

    Sections are emitted in the canonical order and consume the token budget.
    """
    sections_out: dict[str, str] = {}

    # --- ARCHITECTURE ---
    arch_section = _section_header(ARCHITECTURE.title)
    if architecture_text:
        # Heavily truncate existing ARCHITECTURE.md or provide short summary to avoid >10 lines violation
        lines = architecture_text.strip().split("\n")
        # Find first paragraph
        first_p = []
        for line in lines:
            if line.startswith("#"):
                continue
            if not line.strip() and first_p:
                break
            if line.strip():
                first_p.append(line.strip())

        arch_section += " ".join(first_p)[:200]
        arch_section += "\n\n(Architecture truncated. See ARCHITECTURE.md for details.)\n\n"
    else:
        arch_section += _auto_architecture(compressed, root) + "\n\n"
    sections_out[ARCHITECTURE.key] = budget.consume_partial(arch_section)

    # --- DEPENDENCY_GRAPH ---
    graph_section = _section_header(DEPENDENCY_GRAPH.title)
    graph_section += _render_mermaid_graph(dep_graph, root, compressed)

    if dep_graph.cycles:
        graph_section += "### Cyclic Dependencies\n\n"
        graph_section += "> [!WARNING]\n> The following circular import chains were detected:\n\n"
        sorted_cycles = sorted(
            dep_graph.cycles,
            key=lambda cycle: [p.relative_to(root).as_posix() for p in cycle],
        )
        for i, cycle in enumerate(sorted_cycles, 1):
            rel_paths = [p.relative_to(root).as_posix() for p in cycle]
            chain = " -> ".join(f"`{r}`" for r in rel_paths)
            graph_section += f"{i}. {chain}\n"
        graph_section += "\n"
    sections_out[DEPENDENCY_GRAPH.key] = budget.consume_partial(graph_section)

    # --- ENTRY_POINTS & CORE_MODULES ---
    entry_files = []
    core_files = []
    for cf in compressed:
        if cf.tier == 1:
            if cf.path.name in ENTRYPOINT_FILENAMES:
                entry_files.append(cf)
            else:
                core_files.append(cf)

    entry_section = _section_header(ENTRY_POINTS.title)
    if entry_files:
        for cf in entry_files:
            entry_section += cf.content + "\n"
    else:
        entry_section += "*No entry points identified within budget.*\n\n"
    sections_out[ENTRY_POINTS.key] = budget.consume_partial(entry_section)

    # --- SYMBOL_INDEX ---
    symbol_section = _section_header(SYMBOL_INDEX.title)
    if parse_results:
        symbol_lines = []
        count = 0
        for cf in compressed:
            if cf.tier in (1, 2) and cf.path in parse_results:
                pr = parse_results[cf.path]
                if pr.symbols:
                    # Collect symbols
                    for sym in pr.symbols:
                        if count >= 100:
                            break
                        symbol_lines.append(sym.name)
                        if getattr(sym, "children", None):
                            for child in sym.children:
                                symbol_lines.append(f"  {child.name}()")
                        else:
                            # if it's a function without children, just print it?
                            if sym.kind in ("function", "method"):
                                symbol_lines[-1] += "()"
                        symbol_lines.append("")
                        count += 1
            if count >= 100:
                break

        if symbol_lines:
            symbol_section += "\n".join(symbol_lines)
        else:
            symbol_section += "*No symbols found within budget.*\n\n"
    else:
        symbol_section += "*No symbol data available.*\n\n"

    sections_out[SYMBOL_INDEX.key] = budget.consume_partial(symbol_section)

    # --- IMPORTANT_CALL_PATHS ---
    call_paths_section = _section_header(IMPORTANT_CALL_PATHS.title)
    call_paths = dep_graph.detect_call_paths(max_depth=5)

    if call_paths and parse_results:
        import_lines = []
        for path in call_paths:
            for i, node_path in enumerate(path):
                pr = parse_results.get(node_path)
                sym_name = node_path.stem
                if pr and pr.symbols:
                    # just take the first symbol as the main representative
                    sym_name = f"{node_path.stem}.{pr.symbols[0].name}()"
                elif pr and not pr.symbols:
                    sym_name = f"{node_path.stem}()"

                if i == 0:
                    import_lines.append(sym_name)
                else:
                    import_lines.append(f"  → {sym_name}")
            import_lines.append("")

        call_paths_section += "\n".join(import_lines)
    else:
        call_paths_section += "*No call paths detected.*\n\n"

    sections_out[IMPORTANT_CALL_PATHS.key] = budget.consume_partial(call_paths_section)

    core_section = _section_header(CORE_MODULES.title)
    if core_files:
        for cf in core_files:
            core_section += cf.content + "\n"
    else:
        core_section += "*No core modules selected within budget.*\n\n"
    sections_out[CORE_MODULES.key] = budget.consume_partial(core_section)

    # --- SUPPORTING_MODULES ---
    supporting_files = [cf for cf in compressed if cf.tier == 2]
    supp_section = _section_header(SUPPORTING_MODULES.title)
    if supporting_files:
        for cf in supporting_files:
            supp_section += cf.content + "\n"
    else:
        supp_section += "*No supporting modules selected within budget.*\n\n"
    sections_out[SUPPORTING_MODULES.key] = budget.consume_partial(supp_section)

    # --- PERIPHERY ---
    periph_files = [cf for cf in compressed if cf.tier == 3]
    periph_section = _section_header(PERIPHERY.title)
    if periph_files:
        for cf in periph_files:
            periph_section += cf.content
        periph_section += "\n"
    else:
        periph_section += "*No periphery files selected within budget.*\n\n"
    sections_out[PERIPHERY.key] = budget.consume_partial(periph_section)

    return sections_out


def write_context_file(content: str | dict[str, str], output_path: Path) -> None:
    """Write the assembled context to disk."""
    if isinstance(content, dict):
        # preserve section order from output logic
        content_str = "".join(content.values())
    else:
        content_str = content
    output_path.write_text(content_str, encoding="utf-8")


def write_layer_files(sections: dict[str, str], root: Path) -> None:
    """Write REPO_MAP.md and CORE_CONTEXT.md according to the sections."""
    repo_map_keys = [
        ARCHITECTURE.key,
        ENTRY_POINTS.key,
        SYMBOL_INDEX.key,
        IMPORTANT_CALL_PATHS.key,
        DEPENDENCY_GRAPH.key,
    ]
    core_context_keys = [
        CORE_MODULES.key,
        SUPPORTING_MODULES.key,
    ]

    repo_map_content = "".join(sections.get(k, "") for k in repo_map_keys)
    core_context_content = "".join(sections.get(k, "") for k in core_context_keys)

    (root / "REPO_MAP.md").write_text(repo_map_content, encoding="utf-8")
    (root / "CORE_CONTEXT.md").write_text(core_context_content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section_header(title: str) -> str:
    return f"## {title}\n\n"


def _auto_architecture(compressed: list[CompressedFile], root: Path) -> str:
    """Generate a simple, compressed architecture summary from the file list."""
    # Group files by top-level directory
    dirs: dict[str, int] = {}
    for cf in compressed:
        rel = cf.path.relative_to(root).as_posix()
        parts = rel.split("/")
        top = parts[0] if len(parts) > 1 else "."
        dirs[top] = dirs.get(top, 0) + 1

    lines: list[str] = ["A python-based project composed of the following subsystems:", ""]

    # Sort and take top 5 most populated directories to keep it under 10 lines
    top_dirs = sorted(dirs.items(), key=lambda x: -x[1])[:5]
    for d, count in top_dirs:
        if d != ".":
            lines.append(f"- **{d}/**: Primary subsystem containing {count} files")

    if "." in dirs:
        lines.append("- **Root**: Contains scripts and execution points")

    return "\n".join(lines)


def _render_mermaid_graph(
    dep_graph: DepGraph,
    root: Path,
    compressed: list[CompressedFile],
) -> str:
    """Render the dependency graph as a Mermaid diagram.

    Limited to top N ranked modules to keep the diagram readable.
    """
    # Exclude tests, configs, docs, queries, and build artifacts
    exclude_parts = {
        "tests",
        "test",
        "docs",
        "doc",
        "config",
        "configs",
        "queries",
        "build",
        "dist",
    }

    valid_files = []
    for cf in sorted(compressed, key=lambda cf: (-cf.score, cf.path.as_posix())):
        rel = cf.path.relative_to(root).as_posix()
        parts = set(rel.split("/"))
        if (
            not parts.intersection(exclude_parts)
            and not rel.endswith(".scm")
            and not rel.endswith(".md")
        ):
            valid_files.append(cf)

    # Use the first MAX_MERMAID_NODES files by score
    top_files = valid_files[:MAX_MERMAID_NODES]

    if not top_files:
        return "*No dependency data available.*\n\n"

    top_paths = {cf.path for cf in top_files}

    lines: list[str] = ["```mermaid", "graph LR"]

    # Build safe node IDs
    path_to_id: dict[Path, str] = {}
    for i, cf in enumerate(top_files):
        rel = cf.path.relative_to(root).as_posix()
        node_id = f"f{i}"
        path_to_id[cf.path] = node_id
        # Escape special chars in labels
        label = rel.replace('"', '\\"')
        lines.append(f'    {node_id}["{label}"]')

    # Add edges between top files only
    for cf in top_files:
        src_idx = dep_graph.path_to_idx.get(cf.path)
        if src_idx is None:
            continue
        for neighbor_idx in dep_graph.graph.successor_indices(src_idx):
            neighbor_path = dep_graph.idx_to_path.get(neighbor_idx)
            if neighbor_path and neighbor_path in top_paths:
                src_id = path_to_id[cf.path]
                dst_id = path_to_id[neighbor_path]
                lines.append(f"    {src_id} --> {dst_id}")

    lines.append("```\n\n")
    return "\n".join(lines)
