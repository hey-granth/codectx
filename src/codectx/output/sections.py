"""Section constants for CONTEXT.md output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    """A named section in the output file."""

    key: str
    title: str
    heading_level: int = 2


# Sections in output order
ARCHITECTURE = Section(key="architecture", title="ARCHITECTURE")
DEPENDENCY_GRAPH = Section(key="dependency_graph", title="DEPENDENCY_GRAPH")
ENTRY_POINTS = Section(key="entry_points", title="ENTRY_POINTS")
CORE_MODULES = Section(key="core_modules", title="CORE_MODULES")
PERIPHERY = Section(key="periphery", title="PERIPHERY")
RECENT_CHANGES = Section(key="recent_changes", title="RECENT_CHANGES")

# Ordered list for iteration
SECTION_ORDER: tuple[Section, ...] = (
    ARCHITECTURE,
    DEPENDENCY_GRAPH,
    ENTRY_POINTS,
    CORE_MODULES,
    PERIPHERY,
    RECENT_CHANGES,
)
