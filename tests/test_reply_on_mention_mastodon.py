import logging
import random
from unittest.mock import MagicMock, patch

from mastodon import Mastodon

from hypb.dates_helper import get_current_date, get_current_parashah
from hypb.lang import get_eng_yom_tov, get_heb_yom_tov
from hypb.reply_on_mention_mastodon import main, reply
from hypb.settings import REQUIRED_REPLIER_VARS
from hypb.stream_listener_mastodon import _StreamingListener
from hypb.utils import send_alert


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def create_notification(message, status_id):
    return dotdict({
        "id": random.randint(0, 100),
        "type": "mention",
        "status": dotdict({
            "content": message,
            "id": status_id
        })
    })


class TestMastodon(Mastodon):
    def __init__(self):
        super().__init__(api_base_url="testApi")


def base_flow(mocker, message):
    mastodon: Mastodon = TestMastodon()
    mocker.patch.object(mastodon, "status_reply")
    spy = mocker.spy(mastodon, "status_reply")
    stream_client = _StreamingListener(mastodon)
    status_id = random.randint(0, 100)
    notification = create_notification(message, status_id)
    stream_client.on_notification(notification)
    return spy, notification["status"]


def test_date(mocker):
    spy, notification_status = base_flow(mocker, "What's the date?")
    spy.assert_called_once_with(to_status=notification_status, status=f"The date is:\n{get_current_date(lang='eng')}")


def test_date_heb(mocker):
    spy, notification_status = base_flow(mocker, "מה התאריך?")
    spy.assert_called_once_with(to_status=notification_status, status=f"התאריך הוא:\n{get_current_date(lang='heb')}")


def test_parashah(mocker):
    spy, notification_status = base_flow(mocker, "What's the parashah?")
    spy.assert_called_once_with(to_status=notification_status,
                                status=f"The Parashah is {get_current_parashah(lang='eng')}")


def test_parashah_heb(mocker):
    spy, notification_status = base_flow(mocker, "מה פרשת השבוע?")
    spy.assert_called_once_with(to_status=notification_status,
                                status=f"פרשת השבוע היא פרשת {get_current_parashah(lang='heb')}")


def test_upcoming_holiday(mocker):
    spy, notification_status = base_flow(mocker, "What's the Yom Tov?")
    spy.assert_called_once_with(to_status=notification_status,
                                status=get_eng_yom_tov())


def test_upcoming_holiday_heb(mocker):
    spy, notification_status = base_flow(mocker, "מה החג הקרוב?")
    spy.assert_called_once_with(to_status=notification_status,
                                status=get_heb_yom_tov())


def test_unsupported_command(mocker):
    spy, _ = base_flow(mocker, "What's up dude?")
    spy.assert_not_called()


def test_mention_and_reply_are_logged(mocker, caplog):
    """`docker logs` is the only window into what the replier is doing.

    Without these lines a mention that produced no reply is indistinguishable
    from one that never arrived, which is the case worth debugging.
    """
    with caplog.at_level(logging.INFO, logger="hypb.stream_listener_mastodon"):
        _, status = base_flow(mocker, "What's the date?")

    logged = caplog.text
    assert f"status_id={status['id']}" in logged
    assert "What's the date?".lower() in logged.lower()
    assert "replying to status_id" in logged


def test_unmatched_mention_says_why_it_was_ignored(mocker, caplog):
    with caplog.at_level(logging.INFO, logger="hypb.stream_listener_mastodon"):
        base_flow(mocker, "What's up dude?")

    assert "no keyword matched" in caplog.text


def test_non_mention_notification_is_logged_and_ignored(mocker, caplog):
    listener = _StreamingListener(MagicMock())
    notification = create_notification("hello", status_id=1)
    notification["type"] = "favourite"

    with caplog.at_level(logging.INFO, logger="hypb.stream_listener_mastodon"):
        assert listener.on_notification(notification) is None

    assert "type=favourite" in caplog.text


def test_failure_to_reply_is_logged_with_a_traceback(mocker, caplog):
    """An alert alone loses the stack; the log has to keep it."""
    mastodon = MagicMock()
    mastodon.status_reply.side_effect = RuntimeError("boom")
    mocker.patch("hypb.stream_listener_mastodon.send_alert")
    listener = _StreamingListener(mastodon)

    with caplog.at_level(logging.ERROR, logger="hypb.stream_listener_mastodon"):
        listener.on_notification(create_notification("What's the date?", status_id=7))

    assert "failed to handle mention" in caplog.text
    assert "RuntimeError: boom" in caplog.text


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


def test_reply_supervises_the_stream_instead_of_exiting_when_it_drops():
    """A dropped or cleanly-closed stream must reconnect, not end the process.

    mastodon.social recycles long-lived SSE connections; the blocking
    stream_user() cannot recover from that by itself, so it used to exit 1 and
    fire a Telegram alert on an entirely expected event. reply() now hands the
    stream to StreamSupervisor, which reconnects in place — see
    tests/test_stream_supervisor.py for the retry and alerting behaviour.
    """
    mastodon_client = MagicMock()
    listener = MagicMock()
    with (
        patch("hypb.reply_on_mention_mastodon.get_mastodon_client", return_value=mastodon_client),
        patch("hypb.reply_on_mention_mastodon.get_mastodon_stream_listener", return_value=listener),
        patch("hypb.reply_on_mention_mastodon.StreamSupervisor") as supervisor_cls,
    ):
        reply()

    supervisor_cls.return_value.run.assert_called_once_with()
    kwargs = supervisor_cls.call_args.kwargs
    assert kwargs["alert"] is send_alert, "the supervisor must page through the same alerting path as main()"

    kwargs["run_stream"]()
    mastodon_client.stream_user.assert_called_once_with(listener)


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


class FakeStreamResponse:
    """Replays a raw byte stream the way requests' iter_content does."""

    def __init__(self, payload: bytes):
        self.payload = payload

    def iter_content(self, chunk_size=1):
        for byte in self.payload:
            yield bytes([byte])


# mastodon.social sends a keepalive roughly every 15 seconds: a comment line
# starting with ':', then the blank line that terminates the SSE block.
HEARTBEAT = b":thump\n\n"


def test_heartbeat_does_not_abort_the_stream():
    """A keepalive must not kill the replier.

    mastodon-py 1.8.1's _parse_line() calls handle_heartbeat() for a ':' comment
    and returns the event dict untouched — still empty. The blank line that
    follows then reaches _dispatch({}), which reads event['event'] and raises
    MastodonMalformedEventError. Upstream fixed this in 2.x by guarding
    _dispatch with `if not event: return`; we backport that guard.

    Without the guard this crashes the process roughly every 15 seconds, so the
    always-on replier can never stay up.
    """
    listener = _StreamingListener(mastodon_client=MagicMock())

    listener.handle_stream(FakeStreamResponse(HEARTBEAT))


def test_real_event_still_dispatches_after_a_heartbeat():
    """The guard must skip only empty events, never real ones.

    A guard that swallowed everything would make this test the only thing
    standing between a silent bot and nobody noticing.
    """
    listener = _StreamingListener(mastodon_client=MagicMock())
    received = []
    listener.on_update = received.append

    payload = HEARTBEAT + b'event: update\ndata: {"content": "hello"}\n\n'
    listener.handle_stream(FakeStreamResponse(payload))

    assert len(received) == 1, "the real update event was not dispatched"
    assert received[0]["content"] == "hello"


def _listener_with_notifier(mastodon=None):
    notify = MagicMock(return_value=True)
    return _StreamingListener(mastodon or MagicMock(), notify=notify), notify


def test_replied_mention_is_notified_with_its_outcome():
    listener, notify = _listener_with_notifier()

    listener.on_notification(create_notification("What's the date?", status_id=1))

    notify.assert_called_once()
    message = notify.call_args.args[0]
    assert message.startswith("mastodon mention")
    assert "What's the date?" in message
    assert "outcome: replied" in message


def test_unmatched_mention_is_notified_as_not_replied():
    listener, notify = _listener_with_notifier()

    listener.on_notification(create_notification("What's up dude?", status_id=1))

    assert "outcome: not replied (no keyword matched)" in notify.call_args.args[0]


def test_failed_mention_is_notified_as_failed():
    mastodon = MagicMock()
    mastodon.status_reply.side_effect = RuntimeError("boom")
    listener, notify = _listener_with_notifier(mastodon)

    listener.on_notification(create_notification("What's the date?", status_id=1))

    assert "outcome: failed: RuntimeError('boom')" in notify.call_args.args[0]


def test_non_mention_is_not_notified():
    listener, notify = _listener_with_notifier()
    notification = create_notification("hello", status_id=1)
    notification["type"] = "favourite"

    listener.on_notification(notification)

    notify.assert_not_called()


def test_notifier_failure_does_not_lose_the_reply():
    mastodon = MagicMock()
    listener = _StreamingListener(mastodon, notify=MagicMock(return_value=False))

    listener.on_notification(create_notification("What's the date?", status_id=1))

    mastodon.status_reply.assert_called_once()


def test_default_notifier_is_the_telegram_alert(no_telegram):
    listener = _StreamingListener(MagicMock())

    listener.on_notification(create_notification("What's the date?", status_id=1))

    no_telegram.assert_called_once()
