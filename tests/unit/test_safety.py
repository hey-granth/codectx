"""Tests for safety checks in pipeline flow."""

from __future__ import annotations

from pathlib import Path

from codectx.walker import walk


def test_pipeline_safety_check_does_not_receive_dotvenv_files(tmp_path: Path) -> None:
    """The walker should filter out .venv files before they reach safety checks."""
    cert_path = (
        tmp_path / ".venv" / "lib" / "python3.13" / "site-packages" / "certifi" / "cacert.pem"
    )
    cert_path.parent.mkdir(parents=True)
    cert_path.write_text("fake cert\n")

    main_file = tmp_path / "main.py"
    main_file.write_text("def main():\n    return 1\n")

    # The core of the test: use the walker directly, which is responsible
    # for applying the ignore rules.
    files = walk(tmp_path)

    assert main_file in files
    assert cert_path not in files
    assert all(".venv" not in p.parts for p in files)
