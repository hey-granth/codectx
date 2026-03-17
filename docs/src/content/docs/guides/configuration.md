---
title: Configuration
description: Configuring codectx via YAML and CLI flags.
---

While `codectx` works out of the box with zero configuration, you can fine-tune its behavior.

## The `.codectx.yaml` file

Place a `.codectx.yaml` file in the root of your repository to persist configuration options.

```yaml
# .codectx.yaml
ignore:
  - "**/tests/**"
  - "*.draft.py"

budget:
  max_tokens: 100000

compression:
  strip_comments: true
  collapse_interfaces: false
```

## CLI Overrides

Any value in the YAML file can be overridden via the CLI during generation:

```bash
codectx analyze . --tokens 50000 --strip-comments
```

## Ignoring Files

By default, `codectx` respects your `.gitignore`. You can explicitly ignore additional paths in the YAML configuration or via the CLI:

```bash
codectx analyze . --exclude="docs/**"
```
