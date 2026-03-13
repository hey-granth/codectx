"""Composite file scoring — ranks files by importance."""

from __future__ import annotations

import time
from pathlib import Path

from codectx.config.defaults import (
    CYCLE_PENALTY,
    WEIGHT_ENTRY_PROXIMITY,
    WEIGHT_FAN_IN,
    WEIGHT_GIT_FREQUENCY,
    WEIGHT_RECENCY,
)
from codectx.graph.builder import DepGraph
from codectx.ranker.git_meta import GitFileInfo


from codectx.parser.base import ParseResult

def score_files(
    files: list[Path],
    dep_graph: DepGraph,
    git_meta: dict[Path, GitFileInfo],
    semantic_scores: dict[Path, float] | None = None,
    task: str = "default",
    parse_results: dict[Path, ParseResult] | None = None,
) -> dict[Path, float]:
    """Score each file 0.0–1.0 using a weighted composite.

    Signals:
        git_frequency  (0.35): normalized commit count
        fan_in         (0.35): normalized in-degree
        recency        (0.20): normalized days since last modification
        entry_proximity(0.10): normalized graph distance from entry points

    If semantic_scores are provided (from --query), a 5th signal is added
    with weight 0.20, and other weights are rescaled proportionally.

    All signals are min-max normalized before weighting.
    Files in cycles receive a penalty of -0.10 (floored at 0.0).
    """
    if not files:
        return {}
        
    w_freq = WEIGHT_GIT_FREQUENCY
    w_fan = WEIGHT_FAN_IN
    w_rec = WEIGHT_RECENCY
    w_prox = WEIGHT_ENTRY_PROXIMITY
    w_sym = 0.0
    w_dir = 0.0

    if task == "debug":
        w_rec = 0.5
        w_fan = 0.2
    elif task == "feature":
        w_fan = 0.5
        w_sym = 0.2
    elif task == "architecture":
        w_fan = 0.6
        w_dir = 0.2

    # normalize weights
    total_w = w_freq + w_fan + w_rec + w_prox + w_sym + w_dir
    if total_w > 0:
        w_freq /= total_w
        w_fan /= total_w
        w_rec /= total_w
        w_prox /= total_w
        w_sym /= total_w
        w_dir /= total_w

    # Determine weights — if semantic scores provided, rescale
    has_semantic = semantic_scores is not None and len(semantic_scores) > 0
    if has_semantic:
        semantic_weight = 0.20
        scale = 1.0 - semantic_weight
        w_freq *= scale
        w_fan *= scale
        w_rec *= scale
        w_prox *= scale
        w_sym *= scale
        w_dir *= scale
    else:
        semantic_weight = 0.0

    # Collect raw signals
    raw_freq: dict[Path, float] = {}
    raw_fan_in: dict[Path, float] = {}
    raw_recency: dict[Path, float] = {}
    raw_proximity: dict[Path, float] = {}
    raw_sym: dict[Path, float] = {}
    raw_dir: dict[Path, float] = {}

    now = time.time()
    entry_distances = dep_graph.entry_distances()

    for f in files:
        info = git_meta.get(f)
        raw_freq[f] = float(info.commit_count) if info else 0.0
        raw_fan_in[f] = float(dep_graph.fan_in(f))

        if info:
            days_since = max((now - info.last_modified_ts) / 86400.0, 0.0)
        else:
            days_since = 365.0
        raw_recency[f] = 1.0 / (1.0 + days_since)

        dist = entry_distances.get(f)
        if dist is not None:
            raw_proximity[f] = 1.0 / (1.0 + float(dist))
        else:
            raw_proximity[f] = 0.0

        if parse_results and f in parse_results:
            raw_sym[f] = float(len(parse_results[f].symbols))
        else:
            raw_sym[f] = 0.0
            
        raw_dir[f] = 1.0 / (1.0 + len(f.parts))

    # Min-max normalize each signal
    norm_freq = _min_max_normalize(raw_freq)
    norm_fan = _min_max_normalize(raw_fan_in)
    norm_rec = _min_max_normalize(raw_recency)
    norm_prox = _min_max_normalize(raw_proximity)
    norm_sym = _min_max_normalize(raw_sym)
    norm_dir = _min_max_normalize(raw_dir)

    # Weighted composite
    cyclic = dep_graph.cyclic_files
    scores: dict[Path, float] = {}
    for f in files:
        score = (
            w_freq * norm_freq.get(f, 0.0)
            + w_fan * norm_fan.get(f, 0.0)
            + w_rec * norm_rec.get(f, 0.0)
            + w_prox * norm_prox.get(f, 0.0)
            + w_sym * norm_sym.get(f, 0.0)
            + w_dir * norm_dir.get(f, 0.0)
        )
        if has_semantic and semantic_scores is not None:
            score += semantic_weight * semantic_scores.get(f, 0.0)
        # Apply cycle penalty
        if f in cyclic:
            score -= CYCLE_PENALTY
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
