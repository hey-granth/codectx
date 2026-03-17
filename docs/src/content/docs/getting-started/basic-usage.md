---
title: Basic Usage
description: Common commands and options when using codectx.
---

The `codectx` CLI is designed around simplicity and powerful defaults. 

## The `analyze` command

The core command you will use 99% of the time is `analyze`.

```bash
codectx analyze <path>
```

### Specifying Output

By default, the context file is created as `CONTEXT.md` in the target directory. You can specify a different output path:

```bash
codectx analyze . -o /tmp/custom-context.md
```

### Respecting Token Limits

LLMs have finite context windows. To ensure your context fits cleanly into your target model, use the `--tokens` flag. 

`codectx` will intelligently compress files and strip lower-tier dependencies to fit within this budget.

```bash
codectx analyze . --tokens 60000
```

### Watching for Changes

If you're iterating locally alongside an agent, you can have `codectx` continually update the file as you code:

```bash
codectx watch .
```

This ensures your `CONTEXT.md` is always up to date without needing to manually run `analyze` every time you add an import.

For advanced configurations, see the [CLI Reference](../../reference/cli-reference/).
