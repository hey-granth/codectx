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
    CORE_MODULES,
    SUPPORTING_MODULES,
    PERIPHERY,
)
from codectx.config.defaults import ENTRYPOINT_FILENAMES


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
) -> str:
    """Assemble the full CONTEXT.md content.

    Sections are emitted in the canonical order and consume the token budget.
    """
    parts: list[str] = []

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
    parts.append(budget.consume_partial(entry_section))

    core_section = _section_header(CORE_MODULES.title)
    if core_files:
        for cf in core_files:
            core_section += cf.content + "\n"
    else:
        core_section += "*No core modules selected within budget.*\n\n"
    parts.append(budget.consume_partial(core_section))

    # --- SUPPORTING_MODULES ---
    supporting_files = [cf for cf in compressed if cf.tier == 2]
    supp_section = _section_header(SUPPORTING_MODULES.title)
    if supporting_files:
        for cf in supporting_files:
            supp_section += cf.content + "\n"
    else:
        supp_section += "*No supporting modules selected within budget.*\n\n"
    parts.append(budget.consume_partial(supp_section))

    # --- PERIPHERY ---
    periph_files = [cf for cf in compressed if cf.tier == 3]
    periph_section = _section_header(PERIPHERY.title)
    if periph_files:
        for cf in periph_files:
            periph_section += cf.content
        periph_section += "\n"
    else:
        periph_section += "*No periphery files selected within budget.*\n\n"
    parts.append(budget.consume_partial(periph_section))

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
    """Generate a simple, compressed architecture summary from the file list."""
    # Group files by top-level directory
    dirs: dict[str, int] = {}
    for cf in compressed:
        rel = cf.path.relative_to(root).as_posix()
        parts = rel.split("/")
        top = parts[0] if len(parts) > 1 else "."
        dirs[top] = dirs.get(top, 0) + 1

    lines: list[str] = [
        "A python-based project composed of the following subsystems:",
        ""
    ]
    
    # Sort and take top 5 most populated directories to keep it under 10 lines
    top_dirs = sorted(dirs.items(), key=lambda x: -x[1])[:5]
    for d, count in top_dirs:
        if d != ".":
            lines.append(f"- **{d}/**: Primary subsystem containing {count} files")
            
    if "." in dirs:
        lines.append(f"- **Root**: Contains scripts and execution points")

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
    exclude_parts = {"tests", "test", "docs", "doc", "config", "configs", "queries", "build", "dist"}
    
    valid_files = []
    for cf in sorted(compressed, key=lambda cf: (-cf.score, cf.path.as_posix())):
        rel = cf.path.relative_to(root).as_posix()
        parts = set(rel.split("/"))
        if not parts.intersection(exclude_parts) and not rel.endswith(".scm") and not rel.endswith(".md"):
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
