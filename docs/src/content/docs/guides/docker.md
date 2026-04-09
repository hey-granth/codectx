---
title: Docker
description: Run codectx in a container against repositories on your host.
---

## Run codectx against a host repository

Mount your repository into the container at `/repo` and run `analyze`:

```bash
docker run --rm -v /path/to/repo:/repo ghcr.io/hey-granth/codectx analyze /repo
```

This writes `CONTEXT.md` to `/repo/CONTEXT.md` in the container, which maps to your host repository path.

## Why volume mounting writes to your host

`codectx` reads and writes paths you pass on the CLI. Because `/repo` is a bind mount to your host directory, all output files (for example `CONTEXT.md` or a custom `--output` path) appear directly in your host repo.

Examples:

```bash
docker run --rm -v /path/to/repo:/repo ghcr.io/hey-granth/codectx analyze /repo --output /repo/my-context.md
docker run --rm -v /path/to/repo:/repo ghcr.io/hey-granth/codectx analyze /repo --tokens 60000
docker run --rm -v /path/to/repo:/repo ghcr.io/hey-granth/codectx analyze /repo --task architecture
```

## Linux file permissions

The image runs as a non-root user (`codectx`). On some Linux hosts, bind-mounted files may be owned by your host UID/GID and not writable by the container user.

If you hit permission errors, run with your host user mapping:

```bash
docker run --rm --user $(id -u):$(id -g) -v /path/to/repo:/repo ghcr.io/hey-granth/codectx analyze /repo
```

## Watch mode in Docker

`watch` mode works with the same mount pattern:

```bash
docker run --rm -v /path/to/repo:/repo ghcr.io/hey-granth/codectx watch /repo
```

Stop watching with `Ctrl+C`.

## Pin a version vs latest

Use `latest` for the newest release:

```bash
docker pull ghcr.io/hey-granth/codectx:latest
```

Use a release tag for reproducibility:

```bash
docker pull ghcr.io/hey-granth/codectx:v0.2.0
```

## Semantic extra note

The default image installs only core runtime dependencies from `pyproject.toml`. The optional `[semantic]` extra is not included to keep image size reasonable.

If you need semantic ranking inside Docker, build a custom image that extends the published one:

```dockerfile
FROM ghcr.io/hey-granth/codectx:latest
RUN python -m pip install --no-cache-dir "codectx[semantic]"
```


