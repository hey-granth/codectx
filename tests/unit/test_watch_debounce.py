"""Tests for debounced watch behavior."""

from __future__ import annotations

import time
from pathlib import Path

from codectx.cli import DebouncedHandler, _watch_path_is_relevant


class _Event:
    def __init__(self, src_path: str, is_directory: bool = False) -> None:
        self.src_path = src_path
        self.is_directory = is_directory


def test_debounce_batches_events() -> None:
    fired: list[set[str]] = []
    handler = DebouncedHandler(0.2, lambda paths: fired.append(set(paths)))

    for idx in range(5):
        handler.on_any_event(_Event(f"/tmp/src/file{idx}.py"))

    time.sleep(0.35)
    assert len(fired) == 1
    assert len(fired[0]) == 5


def test_debounce_resets_on_new_event() -> None:
    fired: list[set[str]] = []
    handler = DebouncedHandler(0.3, lambda paths: fired.append(set(paths)))

    handler.on_any_event(_Event("/tmp/src/main.py"))
    time.sleep(0.2)
    handler.on_any_event(_Event("/tmp/src/main.py"))
    time.sleep(0.15)
    assert not fired
    time.sleep(0.25)
    assert len(fired) == 1


def test_non_source_files_do_not_trigger() -> None:
    assert _watch_path_is_relevant(Path("__pycache__/foo.pyc")) is False


def test_source_file_triggers() -> None:
    assert _watch_path_is_relevant(Path("src/main.py")) is True


def test_lock_files_do_not_trigger() -> None:
    assert _watch_path_is_relevant(Path("uv.lock")) is False


def test_custom_debounce_delay() -> None:
    fired: list[float] = []
    started = time.perf_counter()
    handler = DebouncedHandler(0.1, lambda _paths: fired.append(time.perf_counter()))
    handler.on_any_event(_Event("/tmp/src/main.py"))
    time.sleep(0.2)
    assert fired
    assert 0.08 <= fired[0] - started <= 0.3
