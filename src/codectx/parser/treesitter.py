"""Tree-sitter AST extraction — parallel parsing of source files."""

from __future__ import annotations

import logging
import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tree_sitter

from codectx.config.defaults import MAX_PARSER_WORKERS
from codectx.parser.base import ParseResult, Symbol, make_plaintext_result
from codectx.parser.languages import (
    LanguageEntry,
    get_language_for_path,
    get_ts_language_object,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Query file loading
# ---------------------------------------------------------------------------

QUERIES_DIR = Path(__file__).parent / "queries"


def _parse_scm_patterns(text: str) -> list[tuple[str, str]]:
    """Parse S-expression (.scm) text into (node_type, capture_name) pairs.

    Handles nested parentheses like:
        (function_definition name: (identifier) @name) @function
    Returns the *outermost* node_type with its trailing @capture.
    """
    results: list[tuple[str, str]] = []
    i = 0
    while i < len(text):
        if text[i] == "(":
            # Find the node_type (first word after opening paren)
            j = i + 1
            while j < len(text) and text[j] == " ":
                j += 1
            k = j
            while k < len(text) and text[k] not in (" ", ")", "\n"):
                k += 1
            node_type = text[j:k]

            # Find matching closing paren (handle nesting)
            depth = 1
            m = i + 1
            while m < len(text) and depth > 0:
                if text[m] == "(":
                    depth += 1
                elif text[m] == ")":
                    depth -= 1
                m += 1

            # After closing paren, look for @capture
            while m < len(text) and text[m] in (" ", "\t"):
                m += 1
            if m < len(text) and text[m] == "@":
                cap_start = m + 1
                cap_end = cap_start
                while (
                    cap_end < len(text)
                    and text[cap_end].isalnum()
                    or (cap_end < len(text) and text[cap_end] == "_")
                ):
                    cap_end += 1
                capture = text[cap_start:cap_end]
                if node_type and capture:
                    results.append((node_type, capture))
                i = cap_end
            else:
                i = m
        else:
            i += 1
    return results


@dataclass(frozen=True)
class QuerySpec:
    """Parsed query specification from a .scm file."""

    import_types: frozenset[str]
    function_types: frozenset[str]
    class_types: frozenset[str]


def _load_query_spec(language: str) -> QuerySpec | None:
    """Load and parse a .scm query file for the given language."""
    scm_path = QUERIES_DIR / f"{language}.scm"
    if not scm_path.is_file():
        return None

    text = scm_path.read_text(encoding="utf-8")
    import_types: set[str] = set()
    function_types: set[str] = set()
    class_types: set[str] = set()

    for node_type, capture in _parse_scm_patterns(text):
        if capture in ("import", "from_import"):
            import_types.add(node_type)
        elif capture in ("function", "method"):
            function_types.add(node_type)
        elif capture == "class":
            class_types.add(node_type)

    return QuerySpec(
        import_types=frozenset(import_types),
        function_types=frozenset(function_types),
        class_types=frozenset(class_types),
    )


# Module-level cache of loaded query specs
_query_cache: dict[str, QuerySpec | None] = {}


def _get_query_spec(language: str) -> QuerySpec | None:
    """Get cached QuerySpec for a language."""
    if language not in _query_cache:
        _query_cache[language] = _load_query_spec(language)
    return _query_cache[language]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_files(files: list[Path]) -> dict[Path, ParseResult]:
    """Parse multiple files in parallel using ProcessPoolExecutor.

    Files with unsupported languages get a plain-text ParseResult.
    """
    results: dict[Path, ParseResult] = {}

    if not files:
        return results

    # Separate into parseable vs plain-text
    parseable: list[tuple[Path, LanguageEntry]] = []
    for f in files:
        entry = get_language_for_path(f)
        if entry is not None:
            parseable.append((f, entry))
        else:
            source = _read_source(f)
            results[f] = make_plaintext_result(f, source)

    # Parse tree-sitter files in parallel
    if parseable:
        # Serialize the language entry for cross-process transfer
        work_items = [(str(p), e.name, e.ts_module_name) for p, e in parseable]

        ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=MAX_PARSER_WORKERS, mp_context=ctx) as pool:
            parsed = list(pool.map(_parse_single_worker, work_items))

        for pr in parsed:
            results[pr.path] = pr

    return results


def parse_file(path: Path) -> ParseResult:
    """Parse a single file (synchronous, for caching or single-file use)."""
    entry = get_language_for_path(path)
    source = _read_source(path)
    if entry is None:
        return make_plaintext_result(path, source)
    return _extract(path, source, entry)


# ---------------------------------------------------------------------------
# Worker function (must be top-level for pickling)
# ---------------------------------------------------------------------------


def _parse_single_worker(args: tuple[str, str, str]) -> ParseResult:
    """Worker function for ProcessPoolExecutor. Receives serializable args."""
    path_str, lang_name, ts_module_name = args
    path = Path(path_str)
    source = _read_source(path)

    entry = LanguageEntry(name=lang_name, ts_module_name=ts_module_name, extensions=())
    return _extract(path, source, entry)


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _extract(path: Path, source: str, entry: LanguageEntry) -> ParseResult:
    """Extract imports, symbols, and docstrings from source via tree-sitter."""
    try:
        ts_lang = get_ts_language_object(entry)
        parser = tree_sitter.Parser(ts_lang)
        tree = parser.parse(source.encode("utf-8"))
    except Exception as exc:
        logger.warning("tree-sitter parse failed for %s: %s", path, exc)
        return _fallback_parse(path, source, entry.name)

    root_node = tree.root_node

    imports = _extract_imports(root_node, entry.name, source)
    symbols = _extract_symbols(root_node, entry.name, source)
    docstrings = _extract_module_docstrings(root_node, entry.name, source)

    return ParseResult(
        path=path,
        language=entry.name,
        imports=tuple(imports),
        symbols=tuple(symbols),
        docstrings=tuple(docstrings),
        raw_source=source,
        line_count=source.count("\n") + 1 if source else 0,
        partial_parse=False,
    )


def _fallback_parse(path: Path, source: str, language: str) -> ParseResult:
    """Best-effort fallback extraction when tree-sitter parsing fails."""
    imports = _regex_imports(source, language)
    docstrings = _regex_docstrings(source, language)
    return ParseResult(
        path=path,
        language=language,
        imports=tuple(imports),
        symbols=(),
        docstrings=tuple(docstrings),
        raw_source=source,
        line_count=source.count("\n") + 1 if source else 0,
        partial_parse=True,
    )


def _regex_imports(source: str, language: str) -> list[str]:
    """Extract import-like lines via lightweight regex patterns."""
    patterns: dict[str, tuple[str, ...]] = {
        "python": (r"^\s*import\s+.+$", r"^\s*from\s+.+\s+import\s+.+$"),
        "javascript": (
            r"^\s*import\s+.+$",
            r"^\s*const\s+.+\s*=\s*require\(.+\).*$",
            r"^\s*require\(.+\).*$",
        ),
        "typescript": (
            r"^\s*import\s+.+$",
            r"^\s*const\s+.+\s*=\s*require\(.+\).*$",
            r"^\s*require\(.+\).*$",
        ),
        "go": (r'^\s*import\s+\("?.+"?\)?\s*$',),
        "rust": (r"^\s*use\s+.+;$",),
        "java": (r"^\s*import\s+.+;$",),
    }
    selected = patterns.get(language)
    if not selected:
        return []

    imports: list[str] = []
    for line in source.splitlines():
        if any(re.match(pat, line) for pat in selected):
            imports.append(line.strip())
    return imports


def _regex_docstrings(source: str, language: str) -> list[str]:
    """Extract a module-level docstring/comment for fallback parsing."""
    if language != "python":
        return []
    triple = re.match(r"^\s*(?:'''|\"\"\")([\s\S]*?)(?:'''|\"\"\")", source)
    if triple:
        return [triple.group(1).strip()]
    return []


# ---------------------------------------------------------------------------
# Import extraction (per-language)
# ---------------------------------------------------------------------------


def _extract_imports(node: Any, language: str, source: str) -> list[str]:
    """Extract import strings from the AST.

    Uses .scm query spec (data-driven) if available, otherwise falls back
    to manual per-language logic for c, cpp, ruby.
    """
    imports: list[str] = []
    spec = _get_query_spec(language)

    if spec is not None and spec.import_types:
        # Data-driven: walk tree and match node types from .scm spec
        for child in _walk_tree(node):
            if child.type in spec.import_types:
                imports.append(_node_text(child, source))
    elif language in ("c", "cpp"):
        for child in _walk_tree(node):
            if child.type == "preproc_include":
                imports.append(_node_text(child, source))
    elif language == "ruby":
        for child in _walk_tree(node):
            if child.type == "call":
                text = _node_text(child, source)
                if text.startswith(("require", "require_relative")):
                    imports.append(text)

    return imports


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------


def _extract_symbols(node: Any, language: str, source: str) -> list[Symbol]:
    """Extract top-level functions and classes."""
    symbols: list[Symbol] = []

    if language == "python":
        for child in node.children:
            if child.type == "function_definition":
                symbols.append(_python_func_symbol(child, source, "function"))
            elif child.type == "class_definition":
                symbols.append(_python_class_symbol(child, source))
            elif child.type == "decorated_definition":
                # Handle decorated functions/classes
                for sub in child.children:
                    if sub.type == "function_definition":
                        symbols.append(_python_func_symbol(sub, source, "function"))
                    elif sub.type == "class_definition":
                        symbols.append(_python_class_symbol(sub, source))
    elif language in ("javascript", "typescript"):
        for child in node.children:
            if child.type in ("function_declaration", "function"):
                symbols.append(_js_func_symbol(child, source))
            elif child.type == "class_declaration":
                symbols.append(_js_class_symbol(child, source))
            elif child.type in ("export_statement", "export_default_declaration"):
                for sub in child.children:
                    if sub.type in ("function_declaration", "function"):
                        symbols.append(_js_func_symbol(sub, source))
                    elif sub.type == "class_declaration":
                        symbols.append(_js_class_symbol(sub, source))
            elif child.type == "lexical_declaration":
                # const foo = () => {} or const foo = function() {}
                for decl in child.children:
                    if decl.type == "variable_declarator":
                        _maybe_js_arrow(decl, source, symbols)
    elif language == "go":
        for child in node.children:
            if child.type == "function_declaration":
                symbols.append(_go_func_symbol(child, source))
            elif child.type == "method_declaration":
                symbols.append(_go_func_symbol(child, source, kind="method"))
            elif child.type == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        symbols.append(_generic_symbol(spec, source, "class"))
    elif language == "rust":
        for child in node.children:
            if child.type == "function_item":
                symbols.append(_generic_symbol(child, source, "function"))
            elif child.type in ("struct_item", "enum_item", "impl_item", "trait_item"):
                symbols.append(_generic_symbol(child, source, "class"))
    elif language == "java":
        for child in _walk_tree(node):
            if child.type == "method_declaration":
                symbols.append(_generic_symbol(child, source, "function"))
            elif child.type == "class_declaration":
                symbols.append(_generic_symbol(child, source, "class"))
    elif language in ("c", "cpp"):
        for child in node.children:
            if child.type == "function_definition":
                symbols.append(_generic_symbol(child, source, "function"))
            elif child.type in ("struct_specifier", "class_specifier"):
                symbols.append(_generic_symbol(child, source, "class"))
    elif language == "ruby":
        for child in node.children:
            if child.type == "method":
                symbols.append(_generic_symbol(child, source, "function"))
            elif child.type == "class":
                symbols.append(_generic_symbol(child, source, "class"))

    return symbols


# ---------------------------------------------------------------------------
# Module docstring extraction
# ---------------------------------------------------------------------------


def _extract_module_docstrings(node: Any, language: str, source: str) -> list[str]:
    """Extract module-level docstrings."""
    docstrings: list[str] = []

    if language == "python":
        # First expression_statement with a string child
        for child in node.children:
            if child.type == "expression_statement":
                for sub in child.children:
                    if sub.type == "string":
                        text = _node_text(sub, source).strip("\"'")
                        if text:
                            docstrings.append(text)
                break  # Only first expression
            elif child.type not in ("comment",):
                break

    return docstrings


# ---------------------------------------------------------------------------
# Language-specific symbol helpers
# ---------------------------------------------------------------------------


def _python_func_symbol(node: Any, source: str, kind: str) -> Symbol:
    name = ""
    sig_parts: list[str] = []
    docstring = ""

    for child in node.children:
        if child.type == "identifier":
            name = _node_text(child, source)
        elif child.type == "parameters":
            sig_parts.append(_node_text(child, source))
        elif child.type == "type":
            sig_parts.append(f" -> {_node_text(child, source)}")

    # Look for docstring in body
    body = _find_child(node, "block")
    if body:
        docstring = _extract_first_docstring(body, source)

    signature = f"def {name}({', '.join(sig_parts)})" if sig_parts else f"def {name}()"
    # Fix: the parameters node already includes parens
    first_param = sig_parts[0] if sig_parts else "()"
    if first_param.startswith("("):
        signature = f"def {name}{first_param}"
    else:
        signature = f"def {name}({first_param})"

    if len(sig_parts) > 1:
        signature += sig_parts[1]  # return type annotation

    return Symbol(
        name=name,
        kind=kind,
        signature=signature,
        docstring=docstring,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


def _python_class_symbol(node: Any, source: str) -> Symbol:
    name = ""
    docstring = ""
    bases = ""

    for child in node.children:
        if child.type == "identifier":
            name = _node_text(child, source)
        elif child.type == "argument_list":
            bases = _node_text(child, source)

    children = []
    body = _find_child(node, "body") or _find_child(node, "block")
    if body:
        docstring = _extract_first_docstring(body, source)
        for sub in body.children:
            if sub.type == "function_definition":
                children.append(_python_func_symbol(sub, source, "method"))

    signature = f"class {name}{bases}" if bases else f"class {name}"

    return Symbol(
        name=name,
        kind="class",
        signature=signature,
        docstring=docstring,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        children=tuple(children),
    )


def _js_func_symbol(node: Any, source: str) -> Symbol:
    name = ""
    for child in node.children:
        if child.type == "identifier":
            name = _node_text(child, source)
            break

    first_line = _node_text(node, source).split("\n")[0].rstrip(" {")
    return Symbol(
        name=name or "<anonymous>",
        kind="function",
        signature=first_line,
        docstring="",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


def _js_class_symbol(node: Any, source: str) -> Symbol:
    name = ""
    for child in node.children:
        if child.type == "identifier":
            name = _node_text(child, source)
            break

    children = []
    body = _find_child(node, "class_body")
    if body:
        for sub in body.children:
            if sub.type == "method_definition":
                mname = ""
                for mchild in sub.children:
                    if mchild.type == "property_identifier":
                        mname = _node_text(mchild, source)
                        break
                if mname:
                    first_line = _node_text(sub, source).split("\n")[0].rstrip(" {")
                    children.append(Symbol(
                        name=mname,
                        kind="method",
                        signature=first_line,
                        docstring="",
                        start_line=sub.start_point[0] + 1,
                        end_line=sub.end_point[0] + 1,
                    ))

    return Symbol(
        name=name or "<anonymous>",
        kind="class",
        signature=f"class {name}",
        docstring="",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        children=tuple(children),
    )


def _maybe_js_arrow(node: Any, source: str, symbols: list[Symbol]) -> None:
    """Handle `const foo = () => {}` pattern."""
    name = ""
    for child in node.children:
        if child.type == "identifier":
            name = _node_text(child, source)
        elif child.type in ("arrow_function", "function"):
            symbols.append(
                Symbol(
                    name=name or "<anonymous>",
                    kind="function",
                    signature=f"const {name} = ...",
                    docstring="",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )
            return


def _go_func_symbol(node: Any, source: str, kind: str = "function") -> Symbol:
    name = ""
    for child in node.children:
        if child.type in ("identifier", "field_identifier"):
            name = _node_text(child, source)
            break

    first_line = _node_text(node, source).split("\n")[0].rstrip(" {")
    return Symbol(
        name=name,
        kind=kind,
        signature=first_line,
        docstring="",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


def _generic_symbol(node: Any, source: str, kind: str) -> Symbol:
    """Generic symbol extractor — takes first identifier as name."""
    name = ""
    for child in node.children:
        if child.type in ("identifier", "name", "type_identifier"):
            name = _node_text(child, source)
            break

    first_line = _node_text(node, source).split("\n")[0]
    return Symbol(
        name=name or "<unknown>",
        kind=kind,
        signature=first_line.rstrip(" {"),
        docstring="",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


# ---------------------------------------------------------------------------
# Tree helpers
# ---------------------------------------------------------------------------


def _walk_tree(node: Any) -> list[Any]:
    """Iterate over all nodes in the tree (BFS)."""
    nodes: list[Any] = []
    stack = [node]
    while stack:
        current = stack.pop()
        nodes.append(current)
        stack.extend(reversed(current.children))
    return nodes


def _node_text(node: Any, source: str) -> str:
    """Get the source text for a tree-sitter node."""
    return source[node.start_byte : node.end_byte]


def _find_child(node: Any, child_type: str) -> Any | None:
    """Find first child of a given type."""
    for child in node.children:
        if child.type == child_type:
            return child
    return None


def _extract_first_docstring(body_node: Any, source: str) -> str:
    """Extract docstring from the first expression_statement in a body block."""
    for child in body_node.children:
        if child.type == "expression_statement":
            for sub in child.children:
                if sub.type == "string":
                    text = _node_text(sub, source)
                    # Strip triple-quotes
                    for q in ('"""', "'''", '"', "'"):
                        if text.startswith(q) and text.endswith(q):
                            text = text[len(q) : -len(q)]
                            break
                    return text.strip()
            break
        elif child.type not in ("comment", "newline"):
            break
    return ""


def _read_source(path: Path) -> str:
    """Read a source file as UTF-8 text."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return ""
