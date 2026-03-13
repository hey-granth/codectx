"""Configuration loader — reads .codectx.toml or pyproject.toml [tool.codectx]."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib as tomli
except ModuleNotFoundError:
    import tomli

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
    llm_enabled: bool = False
    llm_provider: str = "openai"
    llm_model: str = ""
    query: str = ""
    task: str = "default"
    layers: bool = False
    roots: list[Path] = field(default_factory=list)
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
            loaded = tomli.load(fp)
        if isinstance(loaded, dict):
            file_config = loaded
    else:
        # Fallback to pyproject.toml [tool.codectx]
        pyproject_path = root / "pyproject.toml"
        if pyproject_path.is_file():
            with open(pyproject_path, "rb") as fp:
                data = tomli.load(fp)
            if isinstance(data, dict):
                tool_cfg = data.get("tool")
                if isinstance(tool_cfg, dict):
                    codectx_cfg = tool_cfg.get("codectx")
                    if isinstance(codectx_cfg, dict):
                        file_config = codectx_cfg

    token_budget = _resolve_int("token_budget", cli_overrides, file_config, DEFAULT_TOKEN_BUDGET)
    output_file = Path(
        _resolve_str("output_file", cli_overrides, file_config, str(DEFAULT_OUTPUT_FILE))
    )
    since = _resolve_optional_str("since", cli_overrides, file_config, None)
    verbose = _resolve_bool("verbose", cli_overrides, file_config, False)
    no_git = _resolve_bool("no_git", cli_overrides, file_config, False)
    watch = _resolve_bool("watch", cli_overrides, file_config, False)
    llm_enabled = _resolve_bool("llm_enabled", cli_overrides, file_config, False)
    llm_provider = _resolve_str("llm_provider", cli_overrides, file_config, "openai")
    llm_model = _resolve_str("llm_model", cli_overrides, file_config, "")
    query = _resolve_str("query", cli_overrides, file_config, "")
    task = _resolve_str("task", cli_overrides, file_config, "default")
    layers = _resolve_bool("layers", cli_overrides, file_config, False)

    # Roots: from config or CLI overrides, defaults to [root]
    roots_raw = _resolve("roots", cli_overrides, file_config, None)
    resolved_root = root
    roots: list[Path]
    if roots_raw and isinstance(roots_raw, (list, tuple)):
        roots = [Path(r).resolve() for r in roots_raw]
        # For multi-root, use common parent as the effective root
        if len(roots) > 1:
            import os

            resolved_root = Path(os.path.commonpath([str(r) for r in roots]))
    else:
        roots = [root.resolve()]

    extra_ignore_raw = _resolve("extra_ignore", cli_overrides, file_config, ())
    extra_ignore: tuple[str, ...]
    if isinstance(extra_ignore_raw, (list, tuple)):
        extra_ignore = tuple(str(p) for p in extra_ignore_raw)
    else:
        extra_ignore = ()

    return Config(
        root=resolved_root,
        token_budget=token_budget,
        output_file=output_file,
        since=since,
        verbose=verbose,
        no_git=no_git,
        watch=watch,
        llm_enabled=llm_enabled,
        llm_provider=llm_provider,
        llm_model=llm_model,
        query=query,
        task=task,
        layers=layers,
        roots=roots,
        extra_ignore=extra_ignore,
    )


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


def _resolve_bool(
    key: str,
    cli: dict[str, object],
    file_cfg: dict[str, object],
    default: bool,
) -> bool:
    return bool(_resolve(key, cli, file_cfg, default))


def _resolve_str(
    key: str,
    cli: dict[str, object],
    file_cfg: dict[str, object],
    default: str,
) -> str:
    return str(_resolve(key, cli, file_cfg, default))


def _resolve_optional_str(
    key: str,
    cli: dict[str, object],
    file_cfg: dict[str, object],
    default: str | None,
) -> str | None:
    value = _resolve(key, cli, file_cfg, default)
    return None if value is None else str(value)


def _resolve_int(
    key: str,
    cli: dict[str, object],
    file_cfg: dict[str, object],
    default: int,
) -> int:
    value = _resolve(key, cli, file_cfg, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Config value for {key!r} must be numeric, got {type(value).__name__}")
