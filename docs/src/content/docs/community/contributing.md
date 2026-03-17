---
title: Contributing
description: How to contribute to codectx development.
---

We welcome contributions to `codectx`! The project aims to become the definitive standard for integrating local codebases with agentic workflows.

## Development Setup

`codectx` requires Python 3.10+ and relies heavily on `uv` for dependency management.

1. Fork and clone the repository.
2. Setup the virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip sync requirements-dev.txt
   ```
3. Install the package in editable mode:
   ```bash
   uv pip install -e .
   ```

## Running the tool locally

Once installed in editable mode, you can test modifications against the `codectx` source itself:

```bash
codectx analyze . -o /tmp/test-context.md
```

## Running Tests

`codectx` maintains a high standard of coverage utilizing `pytest`.

```bash
pytest
```

To run tests across all supported Python versions, use `tox`:

```bash
tox
```

## Submitting a Pull Request

1. Create a feature branch from `main`.
2. Ensure your code satisfies linting requirements (`ruff check .`).
3. Ensure all tests pass.
4. Submit the PR with a clear description of the problem solved.
