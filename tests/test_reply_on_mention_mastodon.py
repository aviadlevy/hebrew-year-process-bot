import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from hypb.dates_helper import get_current_date, get_current_parashah
from hypb.lang import get_eng_yom_tov, get_heb_yom_tov
from hypb.mention_handler import MentionHandler
from hypb.reply_on_mention_mastodon import main, reply
from hypb.settings import REQUIRED_REPLIER_VARS

NOW = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)


def base_flow(message):
    """Push one fresh mention through the real handler and report what it replied."""
    client = MagicMock()
    handler = MentionHandler(client, MagicMock(), max_age=timedelta(minutes=30), now=lambda: NOW)
    notification = {
        "id": "1",
        "type": "mention",
        "created_at": NOW,
        "status": {"id": "7", "content": message},
    }
    handler.handle(notification)
    return client.status_reply, notification["status"]


def test_date():
    spy, status = base_flow("What's the date?")
    assert spy.call_args.kwargs["to_status"] is status
    assert spy.call_args.kwargs["status"] == f"The date is:\n{get_current_date(lang='eng')}"


def test_date_heb():
    spy, _ = base_flow("מה התאריך?")
    assert spy.call_args.kwargs["status"] == f"התאריך הוא:\n{get_current_date(lang='heb')}"


def test_parashah():
    spy, _ = base_flow("What's the parashah?")
    assert spy.call_args.kwargs["status"] == f"The Parashah is {get_current_parashah(lang='eng')}"


def test_parashah_heb():
    spy, _ = base_flow("מה פרשת השבוע?")
    assert spy.call_args.kwargs["status"] == f"פרשת השבוע היא פרשת {get_current_parashah(lang='heb')}"


def test_upcoming_holiday():
    spy, _ = base_flow("What's the Yom Tov?")
    assert spy.call_args.kwargs["status"] == get_eng_yom_tov()


def test_upcoming_holiday_heb():
    spy, _ = base_flow("מה החג הקרוב?")
    assert spy.call_args.kwargs["status"] == get_heb_yom_tov()


def test_unsupported_command():
    spy, _ = base_flow("What's up dude?")
    spy.assert_not_called()


def test_main_returns_2_on_missing_config(monkeypatch, mocker):
    """main() must fail fast on missing config, before ever attempting an alert.

    hypb/utils.py reads TELEGRAM_TOKEN at import time and bakes it into a URL,
    so a missing token makes every alert 404 silently. Validation must return
    before reply() or send_alert() are ever reached.
    """
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.delenv(var, raising=False)

    send_alert = mocker.patch("hypb.reply_on_mention_mastodon.send_alert")

    assert main() == 2
    assert not send_alert.called


def test_bad_log_level_does_not_stop_the_replier(monkeypatch, mocker):
    """A typo in LOG_LEVEL must not be fatal — answering mentions comes first."""
    monkeypatch.setenv("LOG_LEVEL", "verbose")
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.delenv(var, raising=False)
    mocker.patch("hypb.reply_on_mention_mastodon.send_alert")

    assert main() == 2


def test_debug_logging_never_enables_urllib3_request_logging(monkeypatch, mocker):
    """LOG_LEVEL=DEBUG must not publish the Telegram bot token.

    urllib3 logs each request line at DEBUG, and the token is inside the URL
    ("POST /bot<TOKEN>/sendMessage"), so raising our own verbosity must not
    raise urllib3's.
    """
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.delenv(var, raising=False)
    mocker.patch("hypb.reply_on_mention_mastodon.send_alert")
    logging.getLogger("urllib3").setLevel(logging.NOTSET)

    main()

    assert not logging.getLogger("urllib3").isEnabledFor(logging.DEBUG)


def test_main_returns_1_and_alerts_when_reply_raises(monkeypatch, mocker):
    """When reply() blows up, main() must log it, alert, and return 1.

    reply() only returns by raising now that the supervisor loops forever, so
    anything reaching main()'s handler is a failure the supervisor deliberately
    would not retry — a malformed event, a bad token, a bug — and every one of
    those does deserve a page.
    """
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.setenv(var, "test-value")

    mocker.patch("hypb.reply_on_mention_mastodon.reply", side_effect=RuntimeError("boom"))
    send_alert = mocker.patch("hypb.reply_on_mention_mastodon.send_alert")

    assert main() == 1
    assert send_alert.called


def test_reply_polls_the_feed_through_the_handler_with_the_configured_limits():
    """reply() wires the persistent cursor, the feed, the handler and the poller together."""
    client = MagicMock()
    with (
        patch("hypb.reply_on_mention_mastodon.get_mastodon_client", return_value=client),
        patch("hypb.reply_on_mention_mastodon.MentionCursor") as cursor_cls,
        patch("hypb.reply_on_mention_mastodon.MentionFeed") as feed_cls,
        patch("hypb.reply_on_mention_mastodon.MentionHandler") as handler_cls,
        patch("hypb.reply_on_mention_mastodon.MentionPoller") as poller_cls,
    ):
        reply(max_age=timedelta(minutes=45), poll_interval_seconds=12.0)

    feed_cls.assert_called_once_with(client, cursor_cls.return_value)
    handler_cls.assert_called_once()
    assert handler_cls.call_args.kwargs["max_age"] == timedelta(minutes=45)
    assert poller_cls.call_args.kwargs["policy"].interval_seconds == 12.0
    poller_cls.return_value.run.assert_called_once_with()

    # What the poller runs each tick is the feed, handing mentions to the handler.
    poll = poller_cls.call_args.args[0]
    poll()
    feed_cls.return_value.process_new.assert_called_once_with(handler_cls.return_value.handle)


def test_main_passes_the_environment_settings_to_reply(monkeypatch, mocker):
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.setenv(var, "test-value")
    monkeypatch.setenv("MENTION_MAX_AGE_MINUTES", "10")
    monkeypatch.setenv("POLL_INTERVAL_SECONDS", "15")
    mocker.patch("hypb.reply_on_mention_mastodon.send_alert")
    reply_mock = mocker.patch("hypb.reply_on_mention_mastodon.reply", side_effect=RuntimeError("stop"))

    main()

    reply_mock.assert_called_once_with(timedelta(minutes=10), 15.0)


def test_main_defaults_to_thirty_minutes_and_thirty_seconds(monkeypatch, mocker):
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.setenv(var, "test-value")
    monkeypatch.delenv("MENTION_MAX_AGE_MINUTES", raising=False)
    monkeypatch.delenv("POLL_INTERVAL_SECONDS", raising=False)
    mocker.patch("hypb.reply_on_mention_mastodon.send_alert")
    reply_mock = mocker.patch("hypb.reply_on_mention_mastodon.reply", side_effect=RuntimeError("stop"))

    main()

    reply_mock.assert_called_once_with(timedelta(minutes=30), 30.0)


def test_main_returns_2_on_a_bad_tuning_value(monkeypatch, mocker, caplog):
    """A typo in the age limit must stop the start, not run with an unintended cutoff."""
    for var in REQUIRED_REPLIER_VARS:
        monkeypatch.setenv(var, "test-value")
    monkeypatch.setenv("MENTION_MAX_AGE_MINUTES", "thirty")
    mocker.patch("hypb.reply_on_mention_mastodon.send_alert")
    reply_mock = mocker.patch("hypb.reply_on_mention_mastodon.reply")

    with caplog.at_level(logging.ERROR):
        assert main() == 2

    assert "MENTION_MAX_AGE_MINUTES" in caplog.text
    reply_mock.assert_not_called()
