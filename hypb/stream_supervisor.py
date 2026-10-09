"""Keeps the Mastodon streaming connection alive across transient failures.

mastodon.social recycles long-lived SSE connections, which surfaces as a
`ChunkedEncodingError` ("Response ended prematurely") wrapped by mastodon-py as
`MastodonNetworkError: Server ceased communication.` The blocking
`stream_user()` cannot recover from that on its own: the reconnect loop in
`mastodon/internals.py::__stream` lives entirely inside the thread used for
`run_async=True`, while the synchronous path is a single `connect_func()`
followed by `handle_stream()` and nothing else.

Letting that exception end the process worked — the container restarts — but it
paged on an expected event, made the restart count useless as a crash-loop
signal, and dropped every mention that arrived during the restart.

This supervisor reconnects in-process instead, and deliberately recovers from
*transport* failures only. The old `while True: try/except Exception` around the
stream is what hid the keepalive parsing bug for so long, so anything that is
not a connection problem still propagates to `main()` and ends the process.
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

#: Failures that mean "the connection broke", never "the code is wrong".
#: MastodonNetworkError also covers MastodonReadTimeout and a non-200 response
#: from the streaming endpoint; MastodonServerError covers a 5xx raised while
#: resolving the streaming base URL; the requests errors escape unwrapped when
#: the connect call itself fails.
RECOVERABLE_ERRORS = (
    MastodonNetworkError,
    MastodonServerError,
    RequestsConnectionError,
    RequestsTimeout,
)

INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 60.0

#: A stream that stayed up this long was accepted by the server and kept alive
#: by at least one keepalive, so the reconnect after it is a fresh attempt, not
#: a retry against a server that is refusing us. Only the backoff resets: the
#: outage clock keeps running, so a stream that is cut every few seconds still
#: pages once it has failed to stay up for minutes.
CONNECTED_STREAM_SECONDS = 5.0

#: A stream that stayed up this long did its job; the drop that ended it is an
#: isolated incident, so the backoff and the outage clock start over.
HEALTHY_STREAM_SECONDS = 60.0

#: How long reconnects must keep failing before this is worth a human's
#: attention. Comfortably longer than the several-minute outages the far end
#: recovers from by itself.
ALERT_AFTER_SECONDS = 300.0


@dataclass(frozen=True)
class RetryPolicy:
    """How patiently to reconnect, and when to give up on staying quiet."""

    initial_backoff_seconds: float = INITIAL_BACKOFF_SECONDS
    max_backoff_seconds: float = MAX_BACKOFF_SECONDS
    connected_stream_seconds: float = CONNECTED_STREAM_SECONDS
    healthy_stream_seconds: float = HEALTHY_STREAM_SECONDS
    alert_after_seconds: float = ALERT_AFTER_SECONDS


class StreamSupervisor:
    """Runs a blocking stream forever, reconnecting when the transport fails.

    `run_stream` is a zero-argument callable that blocks until the stream ends;
    calling it again opens a fresh connection. The clock and sleep functions are
    injected so the retry schedule can be tested without real time passing.
    """

    def __init__(
        self,
        run_stream: Callable[[], None],
        alert: Callable[[str], None],
        *,
        policy: RetryPolicy = RetryPolicy(),
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._run_stream = run_stream
        self._alert = alert
        self._policy = policy
        self._sleep = sleep
        self._monotonic = monotonic

    def run(self) -> None:
        """Stream until an unrecoverable error escapes. Never returns normally."""
        backoff = self._policy.initial_backoff_seconds
        outage_started_at = None
        alerted = False

        while True:
            started_at = self._monotonic()
            reason = self._run_once()
            ended_at = self._monotonic()

            if ended_at - started_at >= self._policy.healthy_stream_seconds:
                if alerted:
                    logger.info("mastodon stream recovered after %.0fs of failed reconnects", ended_at - outage_started_at)
                backoff = self._policy.initial_backoff_seconds
                outage_started_at = None
                alerted = False

            elif ended_at - started_at >= self._policy.connected_stream_seconds:
                backoff = self._policy.initial_backoff_seconds

            if outage_started_at is None:
                outage_started_at = ended_at

            outage_seconds = ended_at - outage_started_at
            if not alerted and outage_seconds >= self._policy.alert_after_seconds:
                self._alert(f"mastodon stream down for {outage_seconds / 60:.0f}m, still retrying. last failure: {reason}")
                alerted = True

            logger.warning("mastodon stream ended (%s); reconnecting in %.0fs", reason, backoff)
            self._sleep(backoff)
            backoff = min(backoff * 2, self._policy.max_backoff_seconds)

    def _run_once(self) -> str:
        """Run the stream to completion and describe how it ended.

        A clean server-side close is reported by mastodon-py as a normal return
        rather than an exception, and for an always-on replier it means exactly
        what a dropped connection means: no more mentions are arriving.
        """
        try:
            self._run_stream()
        except RECOVERABLE_ERRORS as e:
            return repr(e)
        return "server closed the stream"
