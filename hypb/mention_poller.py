"""Runs a poll on a timer, retrying transport failures and paging on a sustained outage.

Only *transport* failures are retried. Anything else -- a rejected token, a bug --
propagates to main(), because retrying it forever would hide exactly the
failures that need a human.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from mastodon.errors import MastodonNetworkError, MastodonServerError
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    Timeout as RequestsTimeout,
)

logger = logging.getLogger(__name__)

#: Failures that mean "Mastodon could not be reached", never "the code is wrong".
RECOVERABLE_ERRORS = (
    MastodonNetworkError,
    MastodonServerError,
    RequestsConnectionError,
    RequestsTimeout,
)

#: The longest a mention waits before the bot looks at it. At 30s the bot sends
#: two requests a minute, about 0.7% of mastodon.social's 300 per 5 minutes.
POLL_INTERVAL_SECONDS = 30.0

#: How long polls must keep failing before it is worth a human's attention.
ALERT_AFTER_SECONDS = 300.0


@dataclass(frozen=True)
class PollPolicy:
    interval_seconds: float = POLL_INTERVAL_SECONDS
    alert_after_seconds: float = ALERT_AFTER_SECONDS


class MentionPoller:
    """Calls `poll` every interval, forever. The clock is injected so tests need no real time."""

    def __init__(
        self,
        poll: Callable[[], None],
        alert: Callable[[str], bool],
        *,
        policy: PollPolicy = PollPolicy(),
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._poll = poll
        self._alert = alert
        self._policy = policy
        self._sleep = sleep
        self._monotonic = monotonic

    def run(self) -> None:
        """Poll until an unrecoverable error escapes. Never returns normally."""
        failing_since = None
        alerted = False

        while True:
            try:
                self._poll()
            except RECOVERABLE_ERRORS as e:
                now = self._monotonic()
                if failing_since is None:
                    failing_since = now
                outage_seconds = now - failing_since
                if not alerted and outage_seconds >= self._policy.alert_after_seconds:
                    self._alert(f"mastodon mention poll failing for {outage_seconds / 60:.0f}m, still retrying. last failure: {e!r}")
                    alerted = True
                logger.warning("mention poll failed (%r); retrying in %.0fs", e, self._policy.interval_seconds)
            else:
                if failing_since is not None:
                    logger.info("mention poll recovered after %.0fs of failures", self._monotonic() - failing_since)
                failing_since = None
                alerted = False
            self._sleep(self._policy.interval_seconds)
