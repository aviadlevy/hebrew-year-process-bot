"""Startup notice and the alerting path it is meant to prove.

Telegram is the bot's only channel for saying anything is wrong, and it fails
quietly: a wrong token or chat id comes back as a 4xx with `ok: false`, not as
a transport error. These tests pin both halves of the fix — a message sent on
every start, and a send path that actually reports rejection.
"""

import logging
from datetime import UTC, datetime

import requests

from hypb.reply_on_mention_mastodon import main
from hypb.settings import REQUIRED_REPLIER_VARS
from hypb.startup import build_startup_message
from hypb.utils import send_alert

FAKE_TOKEN = "123456:fake-bot-token"


def test_startup_message_identifies_the_running_deploy():
    """IMAGE_TAG is the only marker that distinguishes two deploys.

    The container runs one pinned tag and compose's env_file puts it in the
    environment; pyproject's version is static and would say nothing.
    """
    message = build_startup_message(
        env={"IMAGE_TAG": "v4.0.0", "MASTODON_BASE_URL": "https://mastodon.social"},
        now=datetime(2026, 8, 18, 9, 30, 0, tzinfo=UTC),
        hostname="hypb-mastodon-replier",
    )

    assert "hypb mastodon replier started" in message
    assert "version: v4.0.0" in message
    assert "instance: https://mastodon.social" in message
    assert "host: hypb-mastodon-replier" in message
    assert "2026-08-18 09:30:00" in message


def test_startup_message_never_carries_credentials():
    """The notice goes over the network; it must describe the deploy, not unlock it."""
    env = {
        "IMAGE_TAG": "v4.0.0",
        "MASTODON_BASE_URL": "https://mastodon.social",
        "MASTODON_ACCESS_TOKEN": "mastodon-secret",
        "TELEGRAM_TOKEN": FAKE_TOKEN,
    }

    message = build_startup_message(env=env, now=datetime.now(UTC), hostname="host")

    assert "mastodon-secret" not in message
    assert FAKE_TOKEN not in message


def test_startup_message_falls_back_when_metadata_is_absent():
    """A locally-run replier has no IMAGE_TAG; that must not crash the start."""
    message = build_startup_message(env={}, now=datetime.now(UTC), hostname="laptop")

    assert "version: unknown" in message
    assert "instance: unknown" in message


def test_main_announces_itself_before_it_starts_polling(monkeypatch, mocker):
    """The notice is only useful if it precedes the work it is announcing."""
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.setenv(var, "test-value")

    calls = []
    mocker.patch("hypb.reply_on_mention_mastodon.send_alert", side_effect=lambda msg: calls.append("alert") or True)
    mocker.patch("hypb.reply_on_mention_mastodon.reply", side_effect=lambda *a: calls.append("reply"))

    main()

    assert calls[:2] == ["alert", "reply"], "the startup notice did not precede polling"


def test_a_rejected_startup_notice_is_logged_but_does_not_stop_the_replier(monkeypatch, mocker, caplog):
    """Answering mentions matters more than being able to page anyone.

    Broken alerting must be loud in the log without taking the bot down with it.
    """
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.setenv(var, "test-value")

    mocker.patch("hypb.reply_on_mention_mastodon.send_alert", return_value=False)
    reply = mocker.patch("hypb.reply_on_mention_mastodon.reply")

    with caplog.at_level(logging.ERROR):
        main()

    assert reply.called, "a failed startup notice must not prevent the replier from running"
    assert "telegram alerting is not working" in caplog.text


def test_send_alert_reports_a_rejection_instead_of_swallowing_it(mocker, caplog):
    """A bad chat id returns HTTP 400 with ok:false — not an exception.

    The old code returned response.text and no caller looked at it, so this
    failed forever in silence.
    """
    response = mocker.MagicMock(ok=False, status_code=400, text='{"ok":false,"description":"chat not found"}')
    mocker.patch("hypb.utils.requests.post", return_value=response)

    with caplog.at_level(logging.ERROR):
        assert send_alert("hello") is False

    assert "chat not found" in caplog.text


def test_send_alert_confirms_a_delivered_message(mocker):
    mocker.patch("hypb.utils.requests.post", return_value=mocker.MagicMock(ok=True, status_code=200))

    assert send_alert("hello") is True


def test_send_alert_never_logs_the_bot_token(monkeypatch, mocker, caplog):
    """requests bakes the failing URL into its error message, token and all.

    The token is a path segment of the Telegram API URL, so logging a transport
    error raw would publish it to the container logs — which are read far more
    casually than the env file it came from.
    """
    monkeypatch.setattr("hypb.utils.TELEGRAM_TOKEN", FAKE_TOKEN)
    mocker.patch(
        "hypb.utils.requests.post",
        side_effect=requests.ConnectionError(f"Max retries exceeded with url: /bot{FAKE_TOKEN}/sendMessage"),
    )

    with caplog.at_level(logging.ERROR):
        assert send_alert("hello") is False

    assert FAKE_TOKEN not in caplog.text, "the bot token leaked into the log"
    assert "***" in caplog.text


def test_send_alert_cannot_hang_the_replier(mocker):
    """An unbounded post would block the stream indefinitely on a stalled API."""
    post = mocker.patch("hypb.utils.requests.post", return_value=mocker.MagicMock(ok=True))

    send_alert("hello")

    assert post.call_args.kwargs["timeout"] > 0
