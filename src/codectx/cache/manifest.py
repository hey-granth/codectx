import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ManifestOptions:
    budget: int
    format: str
    exclude: list[str]


@dataclass
class Manifest:
    codectx_version: str
    generated_at: float
    repo_root: str
    options: ManifestOptions
    files: dict[str, str]  # relative path -> sha256 hex


def hash_file(path: str | Path) -> str:
    """sha256 hex digest of file content."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_file_hashes(
    file_paths: list[str],
    repo_root: str,
) -> dict[str, str]:
    """
    Returns {relative_path: sha256} for all paths.
    Skips unreadable files silently.
    """
    repo_path = Path(repo_root)
    result = {}
    for file_path in file_paths:
        try:
            abs_path = Path(file_path)
            if not abs_path.is_absolute():
                abs_path = repo_path / file_path
            relative_path = abs_path.relative_to(repo_path).as_posix()
            result[relative_path] = hash_file(abs_path)
        except (OSError, ValueError):
            # Skip unreadable files or files outside repo
            continue
    return result


def load_manifest(manifest_path: Path) -> Manifest | None:
    """
    Returns None if file does not exist, is unreadable, or fails JSON parse.
    Never raises.
    """
    try:
        if not manifest_path.is_file():
            return None
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        options_data = data.get("options", {})
        return Manifest(
            codectx_version=data["codectx_version"],
            generated_at=data["generated_at"],
            repo_root=data["repo_root"],
            options=ManifestOptions(
                budget=options_data["budget"],
                format=options_data["format"],
                exclude=options_data.get("exclude", []),
            ),
            files=data.get("files", {}),
        )
    except (KeyError, TypeError, json.JSONDecodeError, OSError):
        return None


def save_manifest(manifest_path: Path, manifest: Manifest) -> None:
    """
    Atomic write: manifest_path.with_suffix('.json.tmp') then os.replace().
    Never raises — logs warning to stderr on failure.
    """
    data = {
        "codectx_version": manifest.codectx_version,
        "generated_at": manifest.generated_at,
        "repo_root": manifest.repo_root,
        "options": {
            "budget": manifest.options.budget,
            "format": manifest.options.format,
            "exclude": manifest.options.exclude,
        },
        "files": manifest.files,
    }
    tmp_path = manifest_path.with_suffix('.json.tmp')
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        os.replace(tmp_path, manifest_path)
    except OSError as e:
        import sys
        print(f"[codectx] manifest save warning: {e}", file=sys.stderr)


def is_up_to_date(
    manifest: Manifest,
    current_hashes: dict[str, str],
    current_options: ManifestOptions,
    current_version: str,
) -> bool:
    """
    Returns True if and only if ALL of the following hold:
    - manifest.codectx_version == current_version
    - manifest.options == current_options
    - manifest.files == current_hashes  (same keys AND same values)
    Returns False if manifest is None.
    """
    if manifest is None:
        return False
    return (
        manifest.codectx_version == current_version
        and manifest.options.budget == current_options.budget
        and manifest.options.format == current_options.format
        and manifest.options.exclude == current_options.exclude
        and manifest.files == current_hashes
    )
