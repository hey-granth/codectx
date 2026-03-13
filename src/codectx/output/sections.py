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
ENTRY_POINTS = Section(key="entry_points", title="ENTRY_POINTS")
CORE_MODULES = Section(key="core_modules", title="CORE_MODULES")
SUPPORTING_MODULES = Section(key="supporting_modules", title="SUPPORTING_MODULES")
DEPENDENCY_GRAPH = Section(key="dependency_graph", title="DEPENDENCY_GRAPH")
PERIPHERY = Section(key="periphery", title="PERIPHERY")

# Ordered list for iteration
SECTION_ORDER: tuple[Section, ...] = (
    ARCHITECTURE,
    ENTRY_POINTS,
    CORE_MODULES,
    SUPPORTING_MODULES,
    DEPENDENCY_GRAPH,
    PERIPHERY,
)
