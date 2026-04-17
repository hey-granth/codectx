"""codectx — Codebase context compiler for AI agents."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("codectx")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
