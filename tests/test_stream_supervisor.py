"""The replier must survive routine SSE disconnects without paging anyone.

mastodon.social recycles long-lived streaming connections; mastodon-py's
blocking `stream_user()` has no reconnect of its own (the retry loop in
`internals.py::__stream` only runs on the `run_async=True` path), so every
recycle used to end the process and fire a Telegram alert. These tests pin the
behaviour that replaces that: reconnect quietly, alert only once the outage is
sustained, and never swallow an error that isn't a transport failure.
"""

import pytest
from mastodon.errors import (
    MastodonMalformedEventError,
    MastodonNetworkError,
    MastodonServerError,
)
from requests.exceptions import ConnectionError as RequestsConnectionError

from hypb.stream_supervisor import (
    ALERT_AFTER_SECONDS,
    CONNECTED_STREAM_SECONDS,
    HEALTHY_STREAM_SECONDS,
    INITIAL_BACKOFF_SECONDS,
    MAX_BACKOFF_SECONDS,
    RetryPolicy,
    StreamSupervisor,
)


class StopSupervisor(Exception):
    """Ends the supervisor's infinite loop once a test's script is exhausted."""


class FakeClock:
    """A monotonic clock that only advances when something sleeps or blocks."""

    def __init__(self):
        self.now = 0.0
        self.slept = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


class ScriptedStream:
    """Replays scripted (duration, outcome) pairs as if it were a blocking stream.

    An outcome of None models a clean server-side close, which mastodon-py
    reports by returning normally rather than raising.
    """

    def __init__(self, clock, steps):
        self.clock = clock
        self.steps = list(steps)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if not self.steps:
            raise StopSupervisor
        duration, outcome = self.steps.pop(0)
        self.clock.now += duration
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def build(clock, steps, alert, **overrides):
    stream = ScriptedStream(clock, steps)
    supervisor = StreamSupervisor(
        run_stream=stream,
        alert=alert,
        policy=RetryPolicy(alert_after_seconds=10.0, **overrides),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    return supervisor, stream


def run_until_exhausted(supervisor):
    with pytest.raises(StopSupervisor):
        supervisor.run()


@pytest.mark.parametrize(
    "error",
    [
        MastodonNetworkError("Server ceased communication."),
        MastodonServerError("500"),
        RequestsConnectionError("connection refused"),
    ],
)
def test_transport_failures_reconnect_without_alerting(error, mocker):
    """The exact failure seen in production must reconnect silently.

    MastodonNetworkError is what a mid-stream ChunkedEncodingError surfaces as;
    MastodonServerError covers a 5xx while resolving the streaming base URL, and
    a raw requests ConnectionError escapes unwrapped from the connect call.
    """
    clock = FakeClock()
    alert = mocker.MagicMock()
    supervisor, stream = build(clock, [(1.0, error)], alert)

    run_until_exhausted(supervisor)

    assert stream.calls == 2, "the supervisor did not reconnect after a transport failure"
    assert not alert.called, "a single recoverable drop must not page anyone"


def test_clean_server_close_reconnects_without_alerting(mocker):
    """mastodon-py returns normally when the server closes the stream cleanly.

    That is indistinguishable from a drop for an always-on replier, so it has to
    reconnect too rather than fall out of the loop.
    """
    clock = FakeClock()
    alert = mocker.MagicMock()
    supervisor, stream = build(clock, [(1.0, None)], alert)

    run_until_exhausted(supervisor)

    assert stream.calls == 2
    assert not alert.called


def test_backoff_grows_exponentially_and_is_capped(mocker):
    """Reconnecting in a tight loop would hammer the server during an outage."""
    clock = FakeClock()
    failures = [(0.0, MastodonNetworkError("drop"))] * 8
    supervisor, _ = build(clock, failures, mocker.MagicMock())

    run_until_exhausted(supervisor)

    assert clock.slept == [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0]


def test_a_stream_that_did_real_work_resets_the_backoff(mocker):
    """A drop after hours of healthy streaming is a fresh incident, not an outage.

    Without this the backoff would creep toward the cap over the process's
    lifetime and a mention arriving right after a routine recycle would wait a
    full minute for the reconnect.
    """
    clock = FakeClock()
    steps = [
        (0.0, MastodonNetworkError("drop")),
        (0.0, MastodonNetworkError("drop")),
        (HEALTHY_STREAM_SECONDS + 1, MastodonNetworkError("drop")),
    ]
    supervisor, _ = build(clock, steps, mocker.MagicMock())

    run_until_exhausted(supervisor)

    assert clock.slept == [1.0, 2.0, 1.0], "the healthy stream did not reset the backoff"


def test_a_stream_cut_every_few_seconds_reconnects_immediately(mocker):
    """The server cutting every stream at ~16s must not make the backoff climb.

    Each of those streams connected and was served before it dropped, so the next
    reconnect is a fresh attempt, not a retry against a dead server. Letting the
    backoff grow to its cap left the replier offline for ~60s of every ~76s, and
    streaming never replays what arrived in the gap.
    """
    clock = FakeClock()
    steps = [(16.0, MastodonNetworkError("Server ceased communication."))] * 6
    supervisor, _ = build(clock, steps, mocker.MagicMock())

    run_until_exhausted(supervisor)

    assert clock.slept == [1.0] * 6


def test_a_connection_that_never_came_up_still_backs_off(mocker):
    """The reset must be earned by actually connecting, not just by failing slowly."""
    clock = FakeClock()
    steps = [(CONNECTED_STREAM_SECONDS - 1, MastodonNetworkError("drop"))] * 3
    supervisor, _ = build(clock, steps, mocker.MagicMock())

    run_until_exhausted(supervisor)

    assert clock.slept == [1.0, 2.0, 4.0]


def test_constant_cutting_still_pages_once_the_outage_is_sustained(mocker):
    """Reconnecting fast must not hide a stream that has not stayed up for minutes."""
    clock = FakeClock()
    alert = mocker.MagicMock()
    steps = [(16.0, MastodonNetworkError("Server ceased communication."))] * 4
    supervisor, _ = build(clock, steps, alert)

    run_until_exhausted(supervisor)

    assert alert.call_count == 1


def test_sustained_outage_alerts_exactly_once(mocker):
    """Being unable to reconnect for minutes is a real failure worth paging on.

    One alert per outage, not one per retry — the point of the change is that
    Telegram stays quiet unless something needs a human.
    """
    clock = FakeClock()
    alert = mocker.MagicMock()
    failures = [(0.0, MastodonNetworkError("drop"))] * 8
    supervisor, _ = build(clock, failures, alert)

    run_until_exhausted(supervisor)

    assert alert.call_count == 1
    message = alert.call_args[0][0]
    assert "MastodonNetworkError" in message, "the alert must name the failure"


def test_alert_rearms_after_the_stream_recovers(mocker):
    """A second outage, after a recovery, must page again rather than stay muted."""
    clock = FakeClock()
    alert = mocker.MagicMock()
    outage = [(0.0, MastodonNetworkError("drop"))] * 8
    steps = outage + [(HEALTHY_STREAM_SECONDS + 1, MastodonNetworkError("drop"))] + outage
    supervisor, _ = build(clock, steps, alert)

    run_until_exhausted(supervisor)

    assert alert.call_count == 2


def test_a_malformed_event_is_never_swallowed(mocker):
    """Parsing bugs must stay loud.

    A MastodonMalformedEventError is what the keepalive bug raised, and the old
    `while True: try/except` around the stream is precisely what kept it hidden
    for so long. Only transport failures are recoverable here.
    """
    clock = FakeClock()
    alert = mocker.MagicMock()
    supervisor, stream = build(clock, [(1.0, MastodonMalformedEventError("Missing field"))], alert)

    with pytest.raises(MastodonMalformedEventError):
        supervisor.run()

    assert stream.calls == 1, "the supervisor retried an error it cannot recover from"
    assert not alert.called, "alerting on fatal errors belongs to main(), not the supervisor"


def test_defaults_are_the_documented_operational_values():
    """These numbers are quoted in docs/deployment.md; keep them honest."""
    assert INITIAL_BACKOFF_SECONDS == 1.0
    assert MAX_BACKOFF_SECONDS == 60.0
    assert CONNECTED_STREAM_SECONDS == 5.0
    assert HEALTHY_STREAM_SECONDS == 60.0
    assert ALERT_AFTER_SECONDS == 300.0
