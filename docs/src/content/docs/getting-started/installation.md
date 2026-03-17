---
title: Installation
description: How to install and set up codectx on your system.
---

import { Tabs, TabItem } from '@astrojs/starlight/components';

`codectx` is built in Python and can be installed via `pip`, `uv`, or `pipx`.

## Prerequisites

- **Python 3.10+**
- Git (if checking out repositories)

## Installation Methods

We strongly recommend installing `codectx` universally via `uv` or `pipx` to keep its dependencies isolated from your project environments.

<Tabs>
  <TabItem label="uv (Recommended)">
    If you use `uv`, installing `codectx` takes seconds:

    uv tool install codectx

  </TabItem>
<br>
  <TabItem label="pipx">
    For global isolated installation using `pipx`:

    pipx install codectx

  </TabItem>
<br>
  <TabItem label="pip">
    To install directly into an active virtual environment:

    pip install codectx

  </TabItem>
</Tabs>

## Verify Installation

Once installed, verify the CLI is accessible:

```bash
codectx --version
```

If it successfully prints the version, you are ready to use `codectx`. Head over to the [Quick Start](./quick-start/) guide to begin analyzing your codebase.
