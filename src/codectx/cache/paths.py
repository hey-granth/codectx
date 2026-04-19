import hashlib
import os
from pathlib import Path


def get_cache_root(repo_root: str) -> Path:
    """
    Returns ~/.cache/codectx/<repo_hash>/ (or $XDG_CACHE_HOME variant).
    Creates the directory if it does not exist.
    """
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    repo_hash = hashlib.sha256(str(Path(repo_root).resolve()).encode()).hexdigest()[:16]
    cache_dir = base / "codectx" / repo_hash
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_manifest_path(repo_root: str) -> Path:
    return get_cache_root(repo_root) / "manifest.json"


def get_embeddings_path(repo_root: str) -> Path:
    return get_cache_root(repo_root) / "embeddings.lance"
