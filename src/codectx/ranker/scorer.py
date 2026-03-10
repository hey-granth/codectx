"""Composite file scoring — ranks files by importance."""

from __future__ import annotations

import time
from pathlib import Path

from codectx.config.defaults import (
    WEIGHT_ENTRY_PROXIMITY,
    WEIGHT_FAN_IN,
    WEIGHT_GIT_FREQUENCY,
    WEIGHT_RECENCY,
)
from codectx.graph.builder import DepGraph
from codectx.ranker.git_meta import GitFileInfo


def score_files(
    files: list[Path],
    dep_graph: DepGraph,
    git_meta: dict[Path, GitFileInfo],
) -> dict[Path, float]:
    """Score each file 0.0–1.0 using a weighted composite.

    Signals:
        git_frequency  (0.35): normalized commit count
        fan_in         (0.35): normalized in-degree
        recency        (0.20): normalized days since last modification
        entry_proximity(0.10): normalized graph distance from entry points

    All signals are min-max normalized before weighting.
    """
    if not files:
        return {}

    # Collect raw signals
    raw_freq: dict[Path, float] = {}
    raw_fan_in: dict[Path, float] = {}
    raw_recency: dict[Path, float] = {}
    raw_proximity: dict[Path, float] = {}

    now = time.time()
    entry_distances = dep_graph.entry_distances()

    for f in files:
        # Git frequency (commit count)
        info = git_meta.get(f)
        raw_freq[f] = float(info.commit_count) if info else 0.0

        # Fan-in (how many files import this one)
        raw_fan_in[f] = float(dep_graph.fan_in(f))

        # Recency: inverse of days since last modification (more recent = higher)
        if info:
            days_since = max((now - info.last_modified_ts) / 86400.0, 0.0)
        else:
            days_since = 365.0  # unknown = old
        raw_recency[f] = 1.0 / (1.0 + days_since)  # transforms to (0, 1]

        # Entry proximity: inverse of graph distance (closer = higher)
        dist = entry_distances.get(f)
        if dist is not None:
            raw_proximity[f] = 1.0 / (1.0 + float(dist))
        else:
            raw_proximity[f] = 0.0  # unreachable from any entry point

    # Min-max normalize each signal
    norm_freq = _min_max_normalize(raw_freq)
    norm_fan = _min_max_normalize(raw_fan_in)
    # recency and proximity are already ∈ (0, 1], but still normalize for consistency
    norm_rec = _min_max_normalize(raw_recency)
    norm_prox = _min_max_normalize(raw_proximity)

    # Weighted composite
    scores: dict[Path, float] = {}
    for f in files:
        score = (
            WEIGHT_GIT_FREQUENCY * norm_freq.get(f, 0.0)
            + WEIGHT_FAN_IN * norm_fan.get(f, 0.0)
            + WEIGHT_RECENCY * norm_rec.get(f, 0.0)
            + WEIGHT_ENTRY_PROXIMITY * norm_prox.get(f, 0.0)
        )
        scores[f] = round(min(max(score, 0.0), 1.0), 6)

    return scores


def _min_max_normalize(values: dict[Path, float]) -> dict[Path, float]:
    """Min-max normalize values to [0, 1]. Returns 0 for all if constant."""
    if not values:
        return {}

    min_val = min(values.values())
    max_val = max(values.values())
    span = max_val - min_val

    if span == 0.0:
        # All values are the same — normalize to 0.5 or 0.0
        return {k: 0.0 for k in values}

    return {k: (v - min_val) / span for k, v in values.items()}
