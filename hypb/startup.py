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


def build_startup_message(
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    hostname: str | None = None,
) -> str:
    """Describe this instance well enough to tell two deploys apart.

    IMAGE_TAG is the only meaningful version marker: the container runs one
    pinned tag, and compose's `env_file` puts it in the environment. The
    project version in pyproject.toml is static and would just be noise.
    """
    env = os.environ if env is None else env
    now = datetime.now().astimezone() if now is None else now
    hostname = socket.gethostname() if hostname is None else hostname

    return "\n".join(
        [
            "hypb mastodon replier started",
            f"version: {env.get('IMAGE_TAG') or 'unknown'}",
            f"instance: {env.get('MASTODON_BASE_URL') or 'unknown'}",
            f"host: {hostname}",
            f"started: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        ]
    )
