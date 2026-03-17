---
title: CLI Reference
description: Complete reference for the codectx Command Line Interface.
---

## Commands

### `analyze`

The primary command to compile a repository into a Context specification.

```text
Usage: codectx analyze [OPTIONS] [PATH]

Arguments:
  [PATH]  The root directory to analyze (default: `.`)

Options:
  -o, --output <FILE>      Output file path (default: CONTEXT.md)
  -t, --tokens <INT>       Maximum token budget for output
  -e, --exclude <GLOB>     Pattern of files/directories to ignore
  -w, --watch              Watch the directory and rebuild on changes
  --strip-comments         Remove comments from source code before output
  --help                   Show help message
```

### `cache`

Manage the internal graph and parsing cache.

```text
Usage: codectx cache [COMMAND]

Commands:
  clear       Erase all internal cache data
  info        Show cache size and usage statistics
```
