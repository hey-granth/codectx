"""Configuration loader — reads .codectx.toml or pyproject.toml [tool.codectx]."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

from codectx.config.defaults import (
    CONFIG_FILENAME,
    DEFAULT_OUTPUT_FILE,
    DEFAULT_TOKEN_BUDGET,
)


@dataclass(frozen=True)
class Config:
    """Resolved configuration for a codectx run."""

    root: Path
    token_budget: int = DEFAULT_TOKEN_BUDGET
    output_file: Path = DEFAULT_OUTPUT_FILE
    since: str | None = None
    verbose: bool = False
    no_git: bool = False
    watch: bool = False
    extra_ignore: tuple[str, ...] = field(default_factory=tuple)

    @property
    def cache_dir(self) -> Path:
        from codectx.config.defaults import CACHE_DIR_NAME
        return self.root / CACHE_DIR_NAME


def load_config(root: Path, **cli_overrides: object) -> Config:
    """Load config from .codectx.toml → pyproject.toml [tool.codectx] → defaults.

    CLI overrides take highest precedence.
    """
    file_config: dict[str, object] = {}

    # Try .codectx.toml first
    toml_path = root / CONFIG_FILENAME
    if toml_path.is_file():
        with open(toml_path, "rb") as fp:
            file_config = tomllib.load(fp)
    else:
        # Fallback to pyproject.toml [tool.codectx]
        pyproject_path = root / "pyproject.toml"
        if pyproject_path.is_file():
            with open(pyproject_path, "rb") as fp:
                data = tomllib.load(fp)
            file_config = data.get("tool", {}).get("codectx", {})

    # Merge: file_config < cli_overrides
    merged: dict[str, object] = {}

    merged["root"] = root
    merged["token_budget"] = _resolve(
        "token_budget", cli_overrides, file_config, DEFAULT_TOKEN_BUDGET
    )
    merged["output_file"] = Path(
        str(_resolve("output_file", cli_overrides, file_config, str(DEFAULT_OUTPUT_FILE)))
    )
    merged["since"] = _resolve("since", cli_overrides, file_config, None)
    merged["verbose"] = bool(_resolve("verbose", cli_overrides, file_config, False))
    merged["no_git"] = bool(_resolve("no_git", cli_overrides, file_config, False))
    merged["watch"] = bool(_resolve("watch", cli_overrides, file_config, False))

    extra_ignore_raw = _resolve("extra_ignore", cli_overrides, file_config, ())
    if isinstance(extra_ignore_raw, (list, tuple)):
        merged["extra_ignore"] = tuple(str(p) for p in extra_ignore_raw)
    else:
        merged["extra_ignore"] = ()

    return Config(**merged)  # type: ignore[arg-type]


def _resolve(
    key: str,
    cli: dict[str, object],
    file_cfg: dict[str, object],
    default: object,
) -> object:
    """Resolve a config key with precedence: CLI > file > default."""
    cli_val = cli.get(key)
    if cli_val is not None:
        return cli_val
    file_val = file_cfg.get(key)
    if file_val is not None:
        return file_val
    return default
