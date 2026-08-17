FROM ghcr.io/astral-sh/uv:0.9-python3.14-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so this layer caches independently of source changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project --no-editable

COPY README.md ./
COPY pyproject.toml uv.lock ./
COPY hypb ./hypb

# --no-editable installs the package into site-packages, so the venv is
# self-contained and the runtime stage needs no source tree.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable


FROM python:3.14-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --uid 10001 hypb

COPY --from=builder --chown=hypb:hypb /app/.venv /app/.venv

USER hypb
WORKDIR /home/hypb

ENTRYPOINT ["hypb-mastodon-replier"]
