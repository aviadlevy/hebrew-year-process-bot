"""What the replier does with one mention: answer it, leave it, or give up on it."""

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from mastodon.return_types import Notification
from mastodon.types_base import try_cast_recurse

from hypb.mention_handler import MentionHandler

NOW = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)
MAX_AGE = timedelta(minutes=30)


def mention(content="What's the date?", notification_id="629782824", age=timedelta(seconds=5)):
    return {
        "id": notification_id,
        "type": "mention",
        "created_at": NOW - age,
        "account": {"acct": "someone@mastodon.social"},
        "status": {
            "id": "117",
            "content": content,
            "url": "https://mastodon.social/@someone/117",
            "language": "en",
            "visibility": "public",
        },
    }


def build(client=None):
    client = client or MagicMock()
    notify = MagicMock(return_value=True)
    handler = MentionHandler(client, notify, max_age=MAX_AGE, now=lambda: NOW)
    return handler, client, notify


def test_a_matching_mention_is_answered_and_reported():
    handler, client, notify = build()
    notification = mention("What's the date?")

    handler.handle(notification)

    client.status_reply.assert_called_once()
    assert client.status_reply.call_args.kwargs["to_status"] is notification["status"]
    notify.assert_called_once()
    assert "outcome: replied" in notify.call_args.args[0]


def test_the_reply_carries_an_idempotency_key_from_the_notification_id():
    """A crash between posting and saving the cursor must not double-post.

    The poller retries that mention after a restart; Mastodon drops the second
    post when the key repeats.
    """
    handler, client, _ = build()

    handler.handle(mention(notification_id="629782824"))

    assert client.status_reply.call_args.kwargs["idempotency_key"] == "hypb-mention-629782824"


def test_a_mention_with_no_keyword_is_left_alone_but_still_reported():
    handler, client, notify = build()

    handler.handle(mention("What's up dude?"))

    client.status_reply.assert_not_called()
    assert "outcome: not replied (no keyword matched)" in notify.call_args.args[0]


def test_a_mention_older_than_the_limit_is_skipped_and_reported():
    """After a long outage the replier must not answer questions nobody is waiting on."""
    handler, client, notify = build()

    handler.handle(mention(age=MAX_AGE + timedelta(minutes=1)))

    client.status_reply.assert_not_called()
    assert "outcome: skipped, 31 min old" in notify.call_args.args[0]


def test_a_mention_exactly_at_the_limit_is_still_answered():
    handler, client, _ = build()

    handler.handle(mention(age=MAX_AGE))

    client.status_reply.assert_called_once()


def test_a_failed_reply_is_alerted_and_reported_without_raising():
    client = MagicMock()
    client.status_reply.side_effect = RuntimeError("boom")
    handler, _, notify = build(client)

    handler.handle(mention())

    messages = [call.args[0] for call in notify.call_args_list]
    assert any(m.startswith("exception: RuntimeError('boom')") and "Traceback" in m for m in messages)
    assert any("outcome: failed: RuntimeError('boom')" in m for m in messages)


def test_a_notifier_that_reports_failure_does_not_undo_the_reply():
    client = MagicMock()
    handler = MentionHandler(client, MagicMock(return_value=False), max_age=MAX_AGE, now=lambda: NOW)

    handler.handle(mention())

    client.status_reply.assert_called_once()


def test_the_mention_and_the_reply_are_logged(caplog):
    handler, _, _ = build()

    with caplog.at_level(logging.INFO, logger="hypb.mention_handler"):
        handler.handle(mention("What's the date?"))

    assert "status_id=117" in caplog.text
    assert "from=@someone@mastodon.social" in caplog.text
    assert "replying to status_id=117" in caplog.text


def test_an_unmatched_mention_says_why_it_was_ignored(caplog):
    handler, _, _ = build()

    with caplog.at_level(logging.INFO, logger="hypb.mention_handler"):
        handler.handle(mention("What's up dude?"))

    assert "no keyword matched" in caplog.text


def test_a_skipped_mention_says_how_old_it_was(caplog):
    handler, _, _ = build()

    with caplog.at_level(logging.INFO, logger="hypb.mention_handler"):
        handler.handle(mention(age=timedelta(hours=2)))

    assert "too old" in caplog.text


def test_a_failure_is_logged_with_its_traceback(caplog):
    """An alert alone loses the stack; the log has to keep it."""
    client = MagicMock()
    client.status_reply.side_effect = RuntimeError("boom")
    handler, _, _ = build(client)

    with caplog.at_level(logging.ERROR, logger="hypb.mention_handler"):
        handler.handle(mention())

    assert "failed to handle mention" in caplog.text
    assert "RuntimeError: boom" in caplog.text


def test_a_real_mastodon_py_notification_is_handled():
    """The plain dicts above are stand-ins; production hands over mastodon-py's typed objects.

    Ids arrive as strings and created_at as an aware datetime, and the age check
    subtracts it from now, so this is the contract that must hold across a
    mastodon-py upgrade.
    """
    notification = try_cast_recurse(
        Notification,
        {
            "id": "629782824",
            "type": "mention",
            "created_at": "2026-10-09T11:59:55.000Z",
            "account": {"id": "9", "acct": "someone@mastodon.social"},
            "status": {
                "id": "117",
                "content": "<p>What's the date?</p>",
                "url": "https://mastodon.social/@someone/117",
                "created_at": "2026-10-09T11:59:55.000Z",
            },
        },
    )
    handler, client, notify = build()

    handler.handle(notification)

    assert client.status_reply.call_args.kwargs["idempotency_key"] == "hypb-mention-629782824"
    assert "outcome: replied" in notify.call_args.args[0]
