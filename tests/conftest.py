import pytest


@pytest.fixture(autouse=True)
def no_telegram(mocker):
    """No test may reach Telegram: listeners built without a notifier default to send_alert."""
    return mocker.patch("hypb.stream_listener_mastodon.send_alert")
