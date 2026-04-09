FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgit2-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src ./src
COPY main.py ./

RUN python -m pip install --no-cache-dir --upgrade pip build \
    && python -m build --wheel --outdir /dist

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgit2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 codectx \
    && useradd --create-home --home-dir /home/codectx --shell /usr/sbin/nologin --uid 1000 --gid 1000 codectx

WORKDIR /workspace

COPY --from=builder /dist/*.whl /tmp/
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir /tmp/*.whl \
    && rm -rf /tmp/*.whl

USER codectx

ENTRYPOINT ["codectx"]
CMD ["--help"]


