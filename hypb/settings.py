"""Startup configuration checks.

The alerting path reads TELEGRAM_TOKEN at import time and bakes it into a URL,
so a missing token produces a 404 on every alert rather than an error. Failing
loudly at startup is the only way that surfaces.
"""

import os
from collections.abc import Iterable, Mapping

REQUIRED_REPLIER_VARS = (
    "MASTODON_ACCESS_TOKEN",
    "MASTODON_BASE_URL",
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
)

REQUIRED_PROGRESS_VARS = (
    "MASTODON_ACCESS_TOKEN",
    "MASTODON_BASE_URL",
    "MASTODON_USER_ID",
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
    "ACCESS_KEY",
    "ACCESS_SECRET",
    "CONSUMER_KEY",
    "CONSUMER_SECRET",
)


class ConfigurationError(Exception):
    """Raised when required environment variables are absent or empty."""


def missing_variables(required: Iterable[str], env: Mapping[str, str] | None = None) -> list[str]:
    if env is None:
        env = os.environ
    return [name for name in required if not env.get(name, "").strip()]


def require(required: Iterable[str], env: Mapping[str, str] | None = None) -> None:
    missing = missing_variables(required, env)
    if missing:
        raise ConfigurationError("missing required environment variables: " + ", ".join(missing))
