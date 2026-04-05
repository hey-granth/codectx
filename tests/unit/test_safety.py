"""Tests for safety checks in pipeline flow."""

from __future__ import annotations

from pathlib import Path


def test_pipeline_safety_check_does_not_receive_dotvenv_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """find_sensitive_files should only receive files already filtered by the walker."""
    from codectx import safety
    from codectx.cli import _run_pipeline
    from codectx.config.loader import load_config

    cert_path = tmp_path / ".venv" / "lib" / "python3.13" / "site-packages" / "certifi" / "cacert.pem"
    cert_path.parent.mkdir(parents=True)
    cert_path.write_text("fake cert\n")

    main_file = tmp_path / "main.py"
    main_file.write_text("def main():\n    return 1\n")

    seen_files: list[Path] = []
    original_find_sensitive_files = safety.find_sensitive_files

    def _spy_find_sensitive_files(files: list[Path], root: Path) -> list[Path]:
        seen_files.extend(files)
        return original_find_sensitive_files(files, root)

    monkeypatch.setattr(safety, "find_sensitive_files", _spy_find_sensitive_files)

    config = load_config(tmp_path, no_git=True)
    _run_pipeline(config)

    assert seen_files
    assert cert_path not in seen_files
    assert all(".venv" not in p.parts for p in seen_files)
    assert main_file in seen_files

