"""A transport failure is retried quietly; a sustained one pages once; anything else is fatal."""

import logging
from unittest.mock import MagicMock

import pytest
from mastodon.errors import (
    MastodonNetworkError,
    MastodonServerError,
    MastodonUnauthorizedError,
)
from requests.exceptions import ConnectionError as RequestsConnectionError

from hypb.mention_poller import (
    ALERT_AFTER_SECONDS,
    POLL_INTERVAL_SECONDS,
    MentionPoller,
    PollPolicy,
)


class StopPolling(Exception):
    """Ends the poller's infinite loop once a test's script is exhausted."""


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def build(*outcomes):
    """A poller whose poll() replays `outcomes`: None succeeds, an exception is raised."""
    clock = FakeClock()
    poll = MagicMock(side_effect=[*outcomes, StopPolling()])
    alert = MagicMock()
    poller = MentionPoller(poll, alert, sleep=clock.sleep, monotonic=clock.monotonic)
    return poller, poll, alert, clock


def run_until_exhausted(poller):
    with pytest.raises(StopPolling):
        poller.run()


def test_it_polls_every_interval():
    poller, poll, _, clock = build(None, None, None)

    run_until_exhausted(poller)

    assert poll.call_count == 4
    assert clock.slept == [POLL_INTERVAL_SECONDS] * 3


@pytest.mark.parametrize(
    "error",
    [
        MastodonNetworkError("Server ceased communication."),
        MastodonServerError("500"),
        RequestsConnectionError("refused"),
    ],
)
def test_a_transport_failure_is_retried_on_the_next_tick_without_alerting(error):
    poller, poll, alert, clock = build(error, None)

    run_until_exhausted(poller)

    assert poll.call_count == 3
    assert clock.slept[0] == POLL_INTERVAL_SECONDS
    assert not alert.called, "one failed poll must not page anyone"


def test_a_sustained_outage_alerts_exactly_once():
    poller, _, alert, _ = build(*[MastodonNetworkError("down")] * 20)

    run_until_exhausted(poller)

    assert alert.call_count == 1
    assert "MastodonNetworkError" in alert.call_args.args[0]


def test_the_alert_rearms_after_a_recovery():
    outage = [MastodonNetworkError("down")] * 12
    poller, _, alert, _ = build(*outage, None, *outage)

    run_until_exhausted(poller)

    assert alert.call_count == 2


def test_recovery_is_logged(caplog):
    poller, _, _, _ = build(*[MastodonNetworkError("down")] * 12, None)

    with caplog.at_level(logging.INFO, logger="hypb.mention_poller"):
        run_until_exhausted(poller)

    assert "recovered" in caplog.text


def test_a_rejected_token_is_never_swallowed():
    """Retrying a 401 forever would hide the one failure only a human can fix."""
    poller, poll, alert, _ = build(MastodonUnauthorizedError("bad token", 401, "Unauthorized", None))

    with pytest.raises(MastodonUnauthorizedError):
        poller.run()

    assert poll.call_count == 1
    assert not alert.called, "alerting on fatal errors belongs to main(), not the poller"


def test_defaults_are_the_documented_operational_values():
    """These numbers are quoted in docs/deployment.md; keep them honest."""
    assert POLL_INTERVAL_SECONDS == 30.0
    assert ALERT_AFTER_SECONDS == 300.0
    assert PollPolicy() == PollPolicy(interval_seconds=30.0, alert_after_seconds=300.0)
