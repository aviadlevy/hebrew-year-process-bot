"""The startup notice: proof on every deploy that alerting actually works.

Telegram is the only way this bot can tell anyone that something is wrong, and
a wrong token or chat id fails quietly — the API answers `ok: false` rather
than refusing to connect, so nothing in the logs distinguishes "no alerts
because all is well" from "no alerts because none can be delivered". Sending
one message at startup collapses that ambiguity at the single moment someone is
already watching: the deploy.
"""

import os
import socket
from collections.abc import Mapping
from datetime import datetime
from urllib.parse import urlparse

from hypb.telegram_message import TelegramMessage, bold, code, escape, italic


def build_startup_message(
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    hostname: str | None = None,
) -> TelegramMessage:
    """Describe this instance well enough to tell two deploys apart.

    IMAGE_TAG is the only meaningful version marker: the container runs one
    pinned tag, and compose's `env_file` puts it in the environment. The
    project version in pyproject.toml is static and would just be noise.
    """
    env = os.environ if env is None else env
    now = datetime.now().astimezone() if now is None else now
    hostname = socket.gethostname() if hostname is None else hostname

    version = env.get("IMAGE_TAG") or "unknown version"
    # Monospace, so Telegram does not turn the domain into a link.
    instance = code(_instance(env.get("MASTODON_BASE_URL")))
    when = now.strftime("%Y-%m-%d %H:%M %Z")
    return TelegramMessage(f"🟢 {bold('Replier started')} · {escape(version)}\n{instance} · {italic(f'host {hostname} · {when}')}")


def _instance(base_url: str | None) -> str:
    """The instance's host; the value as given when it has no scheme, which Mastodon.py also accepts."""
    if not base_url:
        return "unknown instance"
    return urlparse(base_url).netloc or base_url
