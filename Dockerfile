FROM python:3.11-slim-buster AS python-base

# https://python-poetry.org/docs#ci-recommendations
ENV POETRY_VERSION=1.5.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv

# Tell Poetry where to place its cache and virtual environment
ENV POETRY_CACHE_DIR=/opt/.cache

# Create stage for Poetry installation
FROM python-base AS poetry-base

# Creating a virtual environment just for poetry and install it with pip
RUN python3 -m venv "$POETRY_VENV" \
	&& "$POETRY_VENV"/bin/pip install -U pip setuptools \
	&& "$POETRY_VENV"/bin/pip install poetry==${POETRY_VERSION}

FROM python-base

COPY --from=poetry-base ${POETRY_VENV} ${POETRY_VENV}

ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /hypb

ENV PYTHONPATH "${PYTHONPATH}:/hypb"

COPY poetry.lock pyproject.toml ./

RUN poetry check
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-ansi --without dev

COPY hypb .
