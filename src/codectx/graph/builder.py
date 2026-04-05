"""Dependency graph construction using rustworkx."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import rustworkx

from codectx.config.defaults import ENTRYPOINT_FILENAMES
from codectx.graph.resolver import resolve_import
from codectx.parser.base import ParseResult

logger = logging.getLogger(__name__)


@dataclass
class DepGraph:
    """Dependency graph with file-level nodes and import edges."""

    graph: rustworkx.PyDiGraph = field(default_factory=rustworkx.PyDiGraph)
    path_to_idx: dict[Path, int] = field(default_factory=dict)
    idx_to_path: dict[int, Path] = field(default_factory=dict)
    cycles: list[list[Path]] = field(default_factory=list)

    def add_file(self, path: Path) -> int:
        """Add a file node, returning its index."""
        if path in self.path_to_idx:
            return self.path_to_idx[path]
        idx = self.graph.add_node(path)
        self.path_to_idx[path] = idx
        self.idx_to_path[idx] = path
        return idx

    def add_edge(self, from_path: Path, to_path: Path) -> None:
        """Add a directed edge (from imports to)."""
        src = self.add_file(from_path)
        dst = self.add_file(to_path)
        # Avoid duplicate edges
        if not self.graph.has_edge(src, dst):
            self.graph.add_edge(src, dst, None)

    def fan_in(self, path: Path) -> int:
        """Number of files that import this file (in-degree)."""
        idx = self.path_to_idx.get(path)
        if idx is None:
            return 0
        return self.graph.in_degree(idx)

    def fan_out(self, path: Path) -> int:
        """Number of files this file imports (out-degree)."""
        idx = self.path_to_idx.get(path)
        if idx is None:
            return 0
        return self.graph.out_degree(idx)

    def entry_points(self) -> list[Path]:
        """Detect entry points by filename pattern + fallback to low in-degree."""
        detected: list[Path] = []
        for path in self.path_to_idx:
            if path.name in ENTRYPOINT_FILENAMES:
                detected.append(path)

        if detected:
            return sorted(detected, key=lambda p: p.as_posix())

        # Fallback: files with lowest in-degree
        if not self.path_to_idx:
            return []

        min_in = min(self.fan_in(p) for p in self.path_to_idx)
        fallback = [p for p in self.path_to_idx if self.fan_in(p) == min_in]
        return sorted(fallback, key=lambda p: p.as_posix())

    def graph_distance(self, source: Path, target: Path) -> int | None:
        """BFS shortest distance from source to target. None if unreachable."""
        src_idx = self.path_to_idx.get(source)
        tgt_idx = self.path_to_idx.get(target)
        if src_idx is None or tgt_idx is None:
            return None

        # BFS
        visited: set[int] = {src_idx}
        queue: deque[tuple[int, int]] = deque([(src_idx, 0)])

        while queue:
            current, dist = queue.popleft()
            if current == tgt_idx:
                return dist
            for neighbor in self.graph.successor_indices(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))

        return None

    def entry_distances(self) -> dict[Path, int]:
        """BFS distance from nearest entry point for each file."""
        entries = self.entry_points()
        distances: dict[Path, int] = {}

        for entry in entries:
            entry_idx = self.path_to_idx.get(entry)
            if entry_idx is None:
                continue

            # BFS from this entry point (follow both directions for proximity)
            visited: set[int] = {entry_idx}
            queue: deque[tuple[int, int]] = deque([(entry_idx, 0)])

            while queue:
                current, dist = queue.popleft()
                current_path = self.idx_to_path[current]

                if current_path not in distances or dist < distances[current_path]:
                    distances[current_path] = dist

                # Follow successors (imports)
                for neighbor in self.graph.successor_indices(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, dist + 1))

                # Also follow predecessors (imported by)
                for neighbor in self.graph.predecessor_indices(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, dist + 1))

        return distances

    @property
    def cyclic_files(self) -> set[Path]:
        """Return set of all files participating in at least one cycle."""
        result: set[Path] = set()
        for cycle in self.cycles:
            result.update(cycle)
        return result

    def detect_call_paths(self, max_depth: int = 5) -> list[list[Path]]:
        """Detect important call paths starting from entrypoints.

        Algorithm:
        - start from entrypoints
        - follow dependency graph edges
        - limit depth to max_depth
        - prioritize high fan-in nodes
        """
        paths: list[list[Path]] = []
        entries = self.entry_points()

        for entry in entries:
            current = entry
            path = [current]

            idx = self.path_to_idx.get(current)
            if idx is None:
                continue

            visited = {idx}

            for _ in range(max_depth - 1):
                curr_idx = self.path_to_idx[current]
                successors = list(self.graph.successor_indices(curr_idx))
                if not successors:
                    break

                # Sort by fan-in (in-degree) descending
                successors.sort(key=lambda s: self.graph.in_degree(s), reverse=True)

                next_node = None
                for s in successors:
                    if s not in visited:
                        next_node = s
                        break

                if next_node is None:
                    break

                visited.add(next_node)
                current = self.idx_to_path[next_node]
                path.append(current)

            paths.append(path)

        return paths

    @property
    def node_count(self) -> int:
        return len(self.path_to_idx)

    @property
    def edge_count(self) -> int:
        return self.graph.num_edges()


def build_dependency_graph(
    parse_results: dict[Path, ParseResult],
    root: Path,
) -> DepGraph:
    """Build a dependency graph from parse results.

    Args:
        parse_results: Mapping of file paths to their parse results.
        root: Repository root directory.

    Returns:
        Constructed DepGraph.
    """
    graph = DepGraph()

    # Build set of all known files (POSIX paths relative to root)
    all_files: frozenset[str] = frozenset(p.relative_to(root).as_posix() for p in parse_results)

    # Add all files as nodes first
    for path in parse_results:
        graph.add_file(path)

    # Resolve imports and add edges
    for path, result in parse_results.items():
        for import_text in result.imports:
            resolved = resolve_import(
                import_text=import_text,
                language=result.language,
                source_file=path,
                root=root,
                all_files=all_files,
            )
            for target in resolved:
                if target != path:  # no self-edges
                    graph.add_edge(path, target)

    # Detect cycles
    try:
        cycle_edges = rustworkx.digraph_find_cycle(graph.graph)
        if cycle_edges:
            # cycle_edges is a list of (source_idx, target_idx) tuples
            # Group them into a single cycle path
            cycle_nodes: list[Path] = []
            seen: set[int] = set()
            for src_idx, _tgt_idx in cycle_edges:
                if src_idx not in seen:
                    seen.add(src_idx)
                    p = graph.idx_to_path.get(src_idx)
                    if p is not None:
                        cycle_nodes.append(p)
            if cycle_nodes:
                graph.cycles.append(cycle_nodes)
    except Exception as exc:
        logger.debug("Cycle detection failed: %s", exc)

    logger.info(
        "Dependency graph: %d nodes, %d edges, %d cycles",
        graph.node_count,
        graph.edge_count,
        len(graph.cycles),
    )
    return graph
