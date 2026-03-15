"""Default configuration values and constants for codectx."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Always-ignored patterns (applied before .gitignore and .ctxignore)
# ---------------------------------------------------------------------------

ALWAYS_IGNORE: tuple[str, ...] = (
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "__pycache__",
    "*.pyc",
    "*.log",
    "*.lock",
    "*.sqlite",
    "*.db",
    "*.cache",
    ".codectx_cache",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
    "coverage",
)

# ---------------------------------------------------------------------------
# Token budget
# ---------------------------------------------------------------------------

DEFAULT_TOKEN_BUDGET: int = 120_000
TIKTOKEN_ENCODING: str = "cl100k_base"

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------

WEIGHT_GIT_FREQUENCY: float = 0.40
WEIGHT_FAN_IN: float = 0.40
WEIGHT_RECENCY: float = 0.10
WEIGHT_ENTRY_PROXIMITY: float = 0.10
CYCLE_PENALTY: float = 0.10

# ---------------------------------------------------------------------------
# Entry-point filename patterns (basename matching)
# ---------------------------------------------------------------------------

ENTRYPOINT_FILENAMES: frozenset[str] = frozenset(
    {
        # Python
        "main.py",
        "__main__.py",
        "app.py",
        "cli.py",
        "manage.py",
        # JavaScript / TypeScript
        "index.ts",
        "index.js",
        "index.tsx",
        "index.jsx",
        "server.ts",
        "server.js",
        # Go
        "main.go",
        # Rust
        "main.rs",
        "lib.rs",
        # Java
        "Main.java",
        "Application.java",
        # Ruby
        "Rakefile",
        "config.ru",
    }
)

# ---------------------------------------------------------------------------
# Sensitive-file patterns (for safety.py warnings)
# ---------------------------------------------------------------------------

SENSITIVE_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.crt",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account*.json",
    "*.secret",
    "secrets.yaml",
    "secrets.yml",
)

# ---------------------------------------------------------------------------
# Output defaults
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_FILE: Path = Path("CONTEXT.md")
CONFIG_FILENAME: str = ".codectx.toml"
CACHE_DIR_NAME: str = ".codectx_cache"

# ---------------------------------------------------------------------------
# Mermaid graph limits
# ---------------------------------------------------------------------------

MAX_MERMAID_NODES: int = 25

# ---------------------------------------------------------------------------
# Strict section limits
# ---------------------------------------------------------------------------

MAX_ENTRYPOINT_LINES: int = 300

# ---------------------------------------------------------------------------
# Binary detection
# ---------------------------------------------------------------------------

BINARY_CHECK_BYTES: int = 8192

# ---------------------------------------------------------------------------
# Parallelism
# ---------------------------------------------------------------------------

MAX_PARSER_WORKERS: int | None = None  # defaults to cpu_count
MAX_IO_WORKERS: int = 16
