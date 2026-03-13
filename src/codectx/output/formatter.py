"""Structured markdown formatter — emits CONTEXT.md."""

from __future__ import annotations

from pathlib import Path

from codectx.compressor.budget import TokenBudget
from codectx.compressor.tiered import CompressedFile
from codectx.config.defaults import MAX_MERMAID_NODES
from codectx.graph.builder import DepGraph
from codectx.output.sections import (
    ARCHITECTURE,
    CORE_MODULES,
    DEPENDENCY_GRAPH,
    ENTRY_POINTS,
    PERIPHERY,
    RECENT_CHANGES,
)


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
    recent_changes: str = "",
    roots: list[Path] | None = None,
) -> str:
    """Assemble the full CONTEXT.md content.

    Sections are emitted in the canonical order and consume the token budget.
    """
    parts: list[str] = []

    # --- ARCHITECTURE ---
    arch_section = _section_header(ARCHITECTURE.title)
    if architecture_text:
        arch_section += architecture_text + "\n\n"
    else:
        arch_section += _auto_architecture(compressed, root) + "\n\n"
    parts.append(budget.consume_partial(arch_section))

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
    parts.append(budget.consume_partial(graph_section))

    # --- ENTRY_POINTS ---
    entry_files = [cf for cf in compressed if cf.tier == 1]
    entry_section = _section_header(ENTRY_POINTS.title)
    if entry_files:
        for cf in entry_files:
            entry_section += cf.content + "\n"
    else:
        entry_section += "*No tier-1 files selected within budget.*\n\n"
    parts.append(entry_section)

    # --- CORE_MODULES ---
    core_files = [cf for cf in compressed if cf.tier == 2]
    core_section = _section_header(CORE_MODULES.title)
    if core_files:
        for cf in core_files:
            core_section += cf.content + "\n"
    else:
        core_section += "*No tier-2 files selected within budget.*\n\n"
    parts.append(core_section)

    # --- PERIPHERY ---
    periph_files = [cf for cf in compressed if cf.tier == 3]
    periph_section = _section_header(PERIPHERY.title)
    if periph_files:
        for cf in periph_files:
            periph_section += cf.content
        periph_section += "\n"
    else:
        periph_section += "*No tier-3 files selected within budget.*\n\n"
    parts.append(periph_section)

    # --- RECENT_CHANGES ---
    rc_section = _section_header(RECENT_CHANGES.title)
    if recent_changes:
        rc_section += recent_changes + "\n\n"
        parts.append(budget.consume_partial(rc_section))
    else:
        rc_section += "*No recent changes included.*\n\n"
        parts.append(rc_section)

    return "".join(parts)


def write_context_file(content: str, output_path: Path) -> None:
    """Write the assembled context to disk."""
    output_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section_header(title: str) -> str:
    return f"## {title}\n\n"


def _auto_architecture(compressed: list[CompressedFile], root: Path) -> str:
    """Generate a simple architecture summary from the file list."""
    # Group files by top-level directory
    dirs: dict[str, list[str]] = {}
    for cf in compressed:
        rel = cf.path.relative_to(root).as_posix()
        parts = rel.split("/")
        top = parts[0] if len(parts) > 1 else "."
        dirs.setdefault(top, []).append(rel)

    lines: list[str] = ["Project structure overview:\n"]
    for d in sorted(dirs):
        count = len(dirs[d])
        lines.append(f"- **{d}/**: {count} file{'s' if count > 1 else ''}")

    return "\n".join(lines)


def _render_mermaid_graph(
    dep_graph: DepGraph,
    root: Path,
    compressed: list[CompressedFile],
) -> str:
    """Render the dependency graph as a Mermaid diagram.

    Limited to top N ranked modules to keep the diagram readable.
    """
    # Use the first MAX_MERMAID_NODES files by score
    top_files: list[CompressedFile] = sorted(
        compressed, key=lambda cf: (-cf.score, cf.path.as_posix())
    )[:MAX_MERMAID_NODES]

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
