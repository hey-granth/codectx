"""Tiered compression — assigns tiers and enforces token budget."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from codectx.compressor.budget import TokenBudget, count_tokens
from codectx.config.defaults import (
    ENTRYPOINT_FILENAMES,
    MAX_ENTRYPOINT_LINES,
)
from codectx.parser.base import ParseResult


@dataclass(frozen=True)
class CompressedFile:
    """A file compressed to its assigned tier."""

    path: Path
    tier: int  # 1, 2, or 3
    score: float
    content: str
    token_count: int
    language: str


_NON_SOURCE_DIRS: frozenset[str] = frozenset(
    {
        "tests",
        "test",
        "docs",
        "doc",
        "examples",
        "example",
        "benchmarks",
        "benchmark",
        "scripts",
        "script",
    }
)

_CONFIG_FILENAMES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "Cargo.toml",
        "Cargo.lock",
        "go.mod",
        "go.sum",
        "requirements.txt",
        "requirements-dev.txt",
        "Makefile",
        "Dockerfile",
        ".dockerignore",
        "tsconfig.json",
        "jest.config.js",
        "jest.config.ts",
        ".eslintrc",
        ".eslintrc.json",
        ".eslintrc.js",
        ".prettierrc",
        "babel.config.js",
        "vite.config.ts",
        "webpack.config.js",
    }
)

_CONFIG_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".toml",
        ".cfg",
        ".ini",
        ".env",
        ".yaml",
        ".yml",
        ".json",
    }
)

_SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".pyi",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".h",
        ".cpp",
        ".cc",
        ".cxx",
        ".hpp",
        ".hxx",
        ".hh",
        ".rb",
    }
)


def is_config_file(path: str, imported_by: set[str] | None = None) -> bool:
    file_path = Path(path)
    if file_path.name in _CONFIG_FILENAMES:
        return True

    suffix = file_path.suffix.lower()
    if suffix not in _CONFIG_EXTENSIONS:
        return False

    if suffix == ".json":
        return not imported_by
    return suffix not in _SOURCE_EXTENSIONS


def _is_non_source(path: Path, root: Path) -> bool:
    """Return True if the file lives under a non-source directory."""
    try:
        parts = set(path.relative_to(root).parts)
    except ValueError:
        return False
    return bool(parts.intersection(_NON_SOURCE_DIRS))


def assign_tiers(
    scores: dict[Path, float],
) -> dict[Path, int]:
    """Assign tiers by score percentile.

    Top 15% -> Tier 1, next 30% -> Tier 2, rest -> Tier 3.
    Ties at the threshold are promoted into the higher tier.
    """
    if not scores:
        return {}

    sorted_scores = sorted(scores.values(), reverse=True)
    n = len(sorted_scores)

    tier1_cutoff_idx = max(1, int(n * 0.15))
    tier2_cutoff_idx = max(2, int(n * 0.45))

    tier1_threshold = sorted_scores[tier1_cutoff_idx - 1]
    tier2_threshold = sorted_scores[min(tier2_cutoff_idx - 1, n - 1)]

    tiers: dict[Path, int] = {}
    for path, score in scores.items():
        if score >= tier1_threshold:
            tiers[path] = 1
        elif score >= tier2_threshold:
            tiers[path] = 2
        else:
            tiers[path] = 3
    return tiers


def compress_files(
    parse_results: dict[Path, ParseResult],
    scores: dict[Path, float],
    budget: TokenBudget,
    root: Path,
    imported_by_map: dict[Path, set[str]] | None = None,
    llm_enabled: bool = False,
    llm_provider: str = "openai",
    llm_model: str = "",
) -> list[CompressedFile]:
    """Compress files into tiered content within the token budget.

    Budget consumption order:
      1. Tier 1 files (full source), by score descending
      2. Tier 2 files (signatures + docstrings), by score descending
      3. Tier 3 files (one-line summary), by score descending

    Overflow policy: drop Tier 3 → truncate Tier 2 → truncate Tier 1.
    """
    tiers = assign_tiers(scores)

    # Force non-source files to Tier 3 regardless of score
    for path in list(tiers.keys()):
        if _is_non_source(path, root):
            tiers[path] = 3
            continue
        imported_by = imported_by_map.get(path) if imported_by_map else None
        if is_config_file(path.as_posix(), imported_by):
            tiers[path] = 3

    # Group and sort files by score, then path
    def sort_key(p: Path) -> tuple[float, str]:
        return (-scores.get(p, 0.0), p.as_posix())

    sorted_paths = sorted(parse_results.keys(), key=sort_key)

    tier1: list[Path] = []
    tier2: list[Path] = []
    tier3: list[Path] = []

    for path in sorted_paths:
        tier = tiers.get(path, 3)
        if tier == 1:
            tier1.append(path)
        elif tier == 2:
            tier2.append(path)
        else:
            tier3.append(path)

    result: list[CompressedFile] = []

    # Process Tier 1 — full source for entry points, structured summary otherwise
    for path in tier1:
        pr = parse_results[path]
        if path.name in ENTRYPOINT_FILENAMES:
            content = _tier1_content(pr, path, root)
        else:
            content = _structured_summary_content(pr, path, root)
        tokens = count_tokens(content)

        if budget.remaining >= tokens:
            budget.consume(tokens)
            result.append(
                CompressedFile(
                    path=path,
                    tier=1,
                    score=scores.get(path, 0.0),
                    content=content,
                    token_count=tokens,
                    language=pr.language,
                )
            )
        else:
            # Truncate Tier 1 to fit
            truncated = budget.consume_partial(content)
            if truncated:
                result.append(
                    CompressedFile(
                        path=path,
                        tier=1,
                        score=scores.get(path, 0.0),
                        content=truncated,
                        token_count=count_tokens(truncated),
                        language=pr.language,
                    )
                )

    # Process Tier 2 — signatures + docstrings
    for path in tier2:
        if budget.is_exhausted:
            break
        pr = parse_results[path]
        content = _tier2_content(pr, path, root)
        tokens = count_tokens(content)

        if budget.remaining >= tokens:
            budget.consume(tokens)
            result.append(
                CompressedFile(
                    path=path,
                    tier=2,
                    score=scores.get(path, 0.0),
                    content=content,
                    token_count=tokens,
                    language=pr.language,
                )
            )
        else:
            truncated = budget.consume_partial(content)
            if truncated:
                result.append(
                    CompressedFile(
                        path=path,
                        tier=2,
                        score=scores.get(path, 0.0),
                        content=truncated,
                        token_count=count_tokens(truncated),
                        language=pr.language,
                    )
                )

    # Process Tier 3 — one-line summaries (dropped first on overflow)
    # Pre-compute LLM summaries if enabled
    llm_summaries: dict[Path, str] = {}
    if llm_enabled and tier3:
        try:
            from codectx.compressor.summarizer import is_available, summarize_files_batch

            if is_available():
                tier3_results = [parse_results[p] for p in tier3]
                llm_summaries = summarize_files_batch(tier3_results, llm_provider, llm_model)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).debug("LLM summarization failed, using heuristic: %s", exc)

    for path in tier3:
        if budget.is_exhausted:
            break
        pr = parse_results[path]

        # Use LLM summary if available, otherwise heuristic
        if path in llm_summaries and llm_summaries[path]:
            rel = path.relative_to(root).as_posix()
            content = f"- `{rel}` — {llm_summaries[path]}\n"
        else:
            content = _tier3_content(pr, path, root)

        tokens = count_tokens(content)

        if budget.remaining >= tokens:
            budget.consume(tokens)
            result.append(
                CompressedFile(
                    path=path,
                    tier=3,
                    score=scores.get(path, 0.0),
                    content=content,
                    token_count=tokens,
                    language=pr.language,
                )
            )
        # Tier 3 files are simply dropped if they don't fit

    # Sort result for deterministic output: tier → score desc → path
    result.sort(key=lambda cf: (cf.tier, -cf.score, cf.path.as_posix()))

    return result


# ---------------------------------------------------------------------------
# Content generators per tier
# ---------------------------------------------------------------------------


def _tier1_content(pr: ParseResult, path: Path, root: Path) -> str:
    """Tier 1: full source with metadata header."""
    rel = path.relative_to(root).as_posix()
    lang = pr.language if pr.language != "unknown" else ""
    header = f"### `{rel}`\n"

    source = pr.raw_source
    if path.name in ENTRYPOINT_FILENAMES:
        lines = source.split("\n")
        if len(lines) > MAX_ENTRYPOINT_LINES:
            source = "\n".join(lines[:MAX_ENTRYPOINT_LINES])
            source += f"\n\n... (truncated: entry point exceeds {MAX_ENTRYPOINT_LINES} lines)"

    return f"{header}\n```{lang}\n{source}\n```\n"


def _extract_internal_imports(imports: tuple[str, ...], root: Path, source_path: Path) -> list[str]:
    """Extract deterministic internal module identifiers from raw import strings."""
    try:
        src_dir = root / "src"
        package_name = ""
        package_root = root

        if src_dir.is_dir():
            try:
                rel_to_src = source_path.relative_to(src_dir)
                if rel_to_src.parts:
                    candidate = rel_to_src.parts[0]
                    if candidate.isidentifier():
                        package_name = candidate
                        package_root = src_dir / candidate
            except Exception:
                pass

        if not package_name:
            try:
                rel = source_path.relative_to(root)
                if rel.parts:
                    candidate = rel.parts[0]
                    if candidate.isidentifier():
                        package_name = candidate
                        package_root = root / package_name
            except Exception:
                package_name = ""

        if not package_name:
            return []

        try:
            rel_to_pkg = source_path.relative_to(package_root)
            mod_parts = list(rel_to_pkg.with_suffix("").parts)
            current_pkg_parts = mod_parts[:-1]
        except Exception:
            current_pkg_parts = []

        def normalize_name(name: str) -> str:
            return name.strip().split(" as ", 1)[0].strip()

        def is_module_like(name: str) -> bool:
            if not name or name == "*":
                return False
            cleaned = name.replace("_", "")
            return cleaned.isalnum() and name == name.lower()

        def strip_pkg_prefix(module_name: str) -> str:
            if module_name == package_name:
                return ""
            prefix = f"{package_name}."
            if module_name.startswith(prefix):
                return module_name[len(prefix) :]
            return ""

        def module_exists(short_module: str) -> bool:
            if not short_module:
                return False
            try:
                mod_path = package_root.joinpath(*short_module.split("."))
                return (mod_path.with_suffix(".py")).is_file() or (
                    mod_path / "__init__.py"
                ).is_file()
            except Exception:
                return False

        def resolve_relative(module_part: str, imported: list[str]) -> list[str]:
            dots = 0
            for ch in module_part:
                if ch == ".":
                    dots += 1
                else:
                    break
            if dots == 0:
                return []

            remainder = module_part[dots:]
            levels_up = max(0, dots - 1)
            if levels_up > len(current_pkg_parts):
                anchor: list[str] = []
            else:
                anchor = current_pkg_parts[: len(current_pkg_parts) - levels_up]

            remainder_parts = [p for p in remainder.split(".") if p]
            base_parts = anchor + remainder_parts

            out: list[str] = []
            # For "from . import x", avoid adding only the package path itself.
            if remainder_parts:
                base = ".".join(base_parts)
                if base:
                    out.append(base)

            for name in imported:
                if not is_module_like(name):
                    continue
                candidate = ".".join(base_parts + [name]) if base_parts else name
                if candidate:
                    out.append(candidate)
            return out

        modules: set[str] = set()
        for raw in sorted(str(i) for i in imports):
            try:
                text = " ".join(str(raw).strip().split())
                if not text:
                    continue

                if text.startswith("import "):
                    chunk = text[len("import ") :]
                    for part in chunk.split(","):
                        mod = normalize_name(part)
                        short = strip_pkg_prefix(mod)
                        if short and module_exists(short):
                            modules.add(short)
                    continue

                if not text.startswith("from ") or " import " not in text:
                    continue

                left, right = text[len("from ") :].split(" import ", 1)
                module_part = left.strip()
                imported_names = [
                    normalize_name(n.strip("() "))
                    for n in right.split(",")
                    if normalize_name(n.strip("() "))
                ]

                if module_part.startswith("."):
                    for resolved in resolve_relative(module_part, imported_names):
                        if resolved:
                            modules.add(resolved)
                    continue

                short_module = strip_pkg_prefix(module_part)
                if short_module:
                    if short_module and module_exists(short_module):
                        modules.add(short_module)
                    for name in imported_names:
                        if is_module_like(name):
                            candidate = f"{short_module}.{name}" if short_module else name
                            if candidate and module_exists(candidate):
                                modules.add(candidate)
                elif module_part == package_name:
                    for name in imported_names:
                        if is_module_like(name) and module_exists(name):
                            modules.add(name)
            except Exception:
                continue

        return sorted(m for m in modules if m and module_exists(m))
    except Exception:
        return []


def _structured_summary_content(pr: ParseResult, path: Path, root: Path) -> str:
    """Tier 1 (non-entry): deterministic AST-driven structured summary."""
    try:
        rel = path.relative_to(root).as_posix()
    except Exception:
        rel = path.as_posix()

    try:
        purpose = ""
        for d in getattr(pr, "docstrings", ()):
            if isinstance(d, str) and d.strip():
                purpose = d.strip().split("\n", 1)[0].strip()
                break
        if not purpose:
            fallback = path.stem.replace("_", " ").strip() or "module"
            purpose = f"Implements {fallback}."
    except Exception:
        purpose = "Module implementation."

    try:
        imports = _extract_internal_imports(getattr(pr, "imports", ()), root, path)
    except Exception:
        imports = []

    try:
        symbols = list(getattr(pr, "symbols", ()))
    except Exception:
        symbols = []

    def _one_line_doc(doc: str) -> str:
        return doc.strip().split("\n", 1)[0].strip() if isinstance(doc, str) else ""

    def _extract_bases(signature: str) -> str:
        try:
            sig = str(signature)
            start = sig.find("(")
            end = sig.rfind(")")
            if start == -1 or end == -1 or end <= start + 1:
                return ""
            return sig[start + 1 : end].strip()
        except Exception:
            return ""

    def _truncate_signature(signature: str, max_len: int = 120) -> str:
        try:
            sig = str(signature).strip().replace("\n", " ")
            if len(sig) <= max_len:
                return sig
            lpar = sig.find("(")
            rpar = sig.find(")", lpar + 1) if lpar != -1 else -1
            if lpar == -1 or rpar == -1:
                return sig[: max_len - 3] + "..."

            head = sig[: lpar + 1]
            tail = sig[rpar:]
            params = [p.strip() for p in sig[lpar + 1 : rpar].split(",") if p.strip()]
            built = head
            for i, param in enumerate(params):
                chunk = (", " if i else "") + param
                if len(built) + len(chunk) + len(tail) + 4 > max_len:
                    built += "..." if i == 0 else ", ..."
                    break
                built += chunk
            return built + tail
        except Exception:
            text = str(signature)
            return text if len(text) <= max_len else text[: max_len - 3] + "..."

    class_items: list[tuple[str, str, str, list[str]]] = []
    function_items: list[tuple[str, str]] = []
    constant_items: list[str] = []
    allowed_dunder = {"__init__", "__call__", "__str__", "__repr__"}
    constant_name_re = re.compile(r"^[A-Z][A-Z0-9_]*$")

    for sym in sorted(
        symbols,
        key=lambda s: (
            str(getattr(s, "kind", "")),
            str(getattr(s, "name", "")),
            str(getattr(s, "signature", "")),
        ),
    ):
        try:
            kind = str(getattr(sym, "kind", "")).strip()
            name = str(getattr(sym, "name", "")).strip()
            signature = str(getattr(sym, "signature", "")).strip()
            doc = _one_line_doc(getattr(sym, "docstring", ""))

            if kind == "class":
                method_names: list[str] = []
                for child in sorted(
                    getattr(sym, "children", ()), key=lambda c: str(getattr(c, "name", ""))
                ):
                    mname = str(getattr(child, "name", "")).strip()
                    if not mname:
                        continue
                    if not mname.startswith("_") or mname in allowed_dunder:
                        method_names.append(mname)
                class_items.append(
                    (
                        name or "<anonymous>",
                        _extract_bases(signature),
                        doc,
                        sorted(set(method_names)),
                    )
                )
            else:
                function_items.append((_truncate_signature(signature or name), doc))
        except Exception:
            continue

    try:
        import ast

        raw_source = str(getattr(pr, "raw_source", ""))
        parsed = ast.parse(raw_source)
        has_types_or_functions = bool(class_items or function_items)

        for node in parsed.body:
            const_name: str | None = None
            annotation = ""
            value_node: ast.AST | None = None

            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    const_name = target.id
                    value_node = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                const_name = node.target.id
                value_node = node.value
                if node.annotation is not None:
                    annotation_text = ast.get_source_segment(raw_source, node.annotation) or ""
                    annotation = annotation_text.strip()

            if not const_name or value_node is None:
                continue

            include = bool(constant_name_re.match(const_name)) or not has_types_or_functions
            if not include:
                continue

            value_text = ast.get_source_segment(raw_source, value_node) or ""
            value_repr = repr(value_text)
            display_value = value_text.strip() if value_text.strip() else "<complex expression>"
            if len(value_repr) > 80:
                display_value = "<complex expression>"

            if annotation:
                constant_items.append(f"{const_name}: {annotation} = {display_value}")
            else:
                constant_items.append(f"{const_name} = {display_value}")
    except Exception:
        constant_items = []

    notes: list[str] = []
    try:
        if bool(getattr(pr, "partial_parse", False)):
            notes.append("partial parse")
    except Exception:
        pass

    try:
        async_count = 0
        for sym in symbols:
            sig = str(getattr(sym, "signature", "")).lstrip()
            if sig.startswith("async "):
                async_count += 1
            for child in getattr(sym, "children", ()):
                child_sig = str(getattr(child, "signature", "")).lstrip()
                if child_sig.startswith("async "):
                    async_count += 1
        if async_count > 2:
            notes.append(f"async-heavy ({async_count} async functions)")
    except Exception:
        pass

    try:
        raw_source = str(getattr(pr, "raw_source", ""))
        decorator_lines = sum(
            1 for line in raw_source.splitlines() if line.lstrip().startswith("@")
        )
        if decorator_lines > 5:
            notes.append(f"decorator-heavy ({decorator_lines} decorators)")
    except Exception:
        pass

    try:
        line_count = int(getattr(pr, "line_count", 0))
        if line_count > 300:
            notes.append(f"large file ({line_count} lines)")
    except Exception:
        pass

    def _build_summary(
        max_imports: int,
        max_classes: int,
        max_methods: int,
        max_functions: int,
        include_function_docs: bool,
        include_notes: bool,
    ) -> str:
        out: list[str] = [f"### `{rel}`", "", f"**Purpose:** {purpose}"]

        if imports and max_imports > 0:
            shown_imports = imports[:max_imports]
            dep_text = ", ".join(f"`{m}`" for m in shown_imports)
            more_imports = len(imports) - len(shown_imports)
            if more_imports > 0:
                dep_text += f", +{more_imports} more"
            out.append(f"**Depends on:** {dep_text}")

        if class_items and max_classes > 0:
            out.append("")
            out.append("**Types:**")
            for name, bases, doc, methods in class_items[:max_classes]:
                shown_methods = methods[:max_methods]
                more_methods = len(methods) - len(shown_methods)
                bits: list[str] = [f"`{name}`"]
                if bases:
                    bits.append(f"(bases: `{bases}`)")
                if doc:
                    bits.append(f"- {doc}")
                if shown_methods:
                    methods_text = ", ".join(f"`{m}`" for m in shown_methods)
                    if more_methods > 0:
                        methods_text += f" (+{more_methods} more)"
                    bits.append(f"methods: {methods_text}")
                out.append("- " + " ".join(bits))

        if function_items and max_functions > 0:
            out.append("")
            out.append("**Functions:**")
            for signature, doc in function_items[:max_functions]:
                out.append(f"- `{signature}`")
                if include_function_docs and doc:
                    out.append(f"  - {doc}")

        if constant_items:
            out.append("")
            out.append("## Constants")
            for constant_line in constant_items[:20]:
                out.append(constant_line)

        if include_notes and notes:
            out.append("")
            out.append(f"**Notes:** {'; '.join(notes)}")

        out.append("")
        return "\n".join(out)

    compact_profiles = [
        (8, 6, 6, 12, True, True),
        (6, 4, 4, 8, True, True),
        (6, 3, 4, 8, False, True),
        (5, 2, 3, 6, False, False),
        (4, 1, 2, 4, False, False),
    ]

    candidate = _build_summary(*compact_profiles[-1])
    for profile in compact_profiles:
        built = _build_summary(*profile)
        candidate = built
        if count_tokens(built) <= 200:
            return built

    minimal: list[str] = [f"### `{rel}`", "", f"**Purpose:** {purpose}"]
    if function_items:
        minimal.append("")
        minimal.append("**Functions:**")
        minimal.append(f"- `{function_items[0][0]}`")
        if function_items[0][1]:
            minimal.append(f"  - {function_items[0][1]}")
    minimal.append("")
    minimal_text = "\n".join(minimal)
    if count_tokens(minimal_text) <= 200:
        return minimal_text
    return candidate


def _tier2_content(pr: ParseResult, path: Path, root: Path) -> str:
    """Tier 2: function/class signatures + docstrings."""
    rel = path.relative_to(root).as_posix()
    lines: list[str] = [f"### `{rel}`\n"]

    if pr.docstrings:
        lines.append(f"> {pr.docstrings[0]}\n")

    if pr.symbols:
        lang = pr.language if pr.language != "unknown" else ""
        lines.append(f"```{lang}")
        for sym in pr.symbols:
            lines.append(sym.signature)
            if sym.docstring:
                lines.append(f'    """{sym.docstring}"""')
            lines.append("")
        lines.append("```\n")
    else:
        lines.append(f"*{pr.line_count} lines, {len(pr.imports)} imports*\n")

    return "\n".join(lines)


def _tier3_content(pr: ParseResult, path: Path, root: Path) -> str:
    """Tier 3: one-line summary."""
    rel = path.relative_to(root).as_posix()
    summary = _one_line_summary(pr)
    return f"- `{rel}` — {summary}\n"


def _one_line_summary(pr: ParseResult) -> str:
    """Generate a one-line summary from parse result."""
    parts: list[str] = []

    if pr.docstrings:
        # Use first docstring, truncated
        doc = pr.docstrings[0].split("\n")[0][:80]
        return doc

    if pr.symbols:
        kind_counts: dict[str, int] = {}
        for s in pr.symbols:
            kind_counts[s.kind] = kind_counts.get(s.kind, 0) + 1
        for kind, count in sorted(kind_counts.items()):
            parts.append(f"{count} {kind}{'s' if count > 1 else ''}")

    if pr.imports:
        parts.append(f"{len(pr.imports)} imports")

    parts.append(f"{pr.line_count} lines")

    return ", ".join(parts)
