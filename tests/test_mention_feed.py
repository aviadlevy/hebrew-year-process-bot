"""The feed hands over each new mention once, in order, and never re-answers history.

The stream it replaces delivered mentions only while connected, and replayed
nothing after a cut. Here Mastodon is the source of truth: whatever it holds
that is newer than the cursor gets handled, exactly once.
"""

from unittest.mock import MagicMock

import pytest

from hypb.mention_cursor import MentionCursor
from hypb.mention_feed import MentionFeed


class ScriptedMastodon:
    """Answers each notifications() call from a script of pages."""

    def __init__(self, *pages):
        self.pages = list(pages)
        self.calls = []

    def notifications(self, **kwargs):
        self.calls.append(kwargs)
        return self.pages.pop(0)


def note(notification_id):
    return {"id": str(notification_id), "type": "mention"}


def build(tmp_path, *pages, cursor_value=None, page_size=30):
    client = ScriptedMastodon(*pages)
    cursor = MentionCursor(tmp_path / "state.db")
    if cursor_value is not None:
        cursor.set(cursor_value)
    return MentionFeed(client, cursor, page_size=page_size), client, cursor, MagicMock()


def test_the_first_run_starts_from_the_newest_mention_without_answering_anything(tmp_path):
    """A deploy must not re-answer mentions the stream already handled."""
    feed, client, cursor, handle = build(tmp_path, [note(30), note(20)])

    feed.process_new(handle)

    assert cursor.get() == 30
    handle.assert_not_called()
    assert client.calls == [{"types": ["mention"], "limit": 1}]


def test_the_first_run_with_no_mentions_still_records_a_cursor(tmp_path):
    """Otherwise the first mention ever received would be taken for history and skipped."""
    feed, _, cursor, handle = build(tmp_path, [])

    feed.process_new(handle)

    assert cursor.get() == 0
    handle.assert_not_called()


def test_new_mentions_are_handled_oldest_first(tmp_path):
    """Mastodon returns a page newest-first; the oldest question gets answered first."""
    feed, _, cursor, handle = build(tmp_path, [note(30), note(10), note(20)], cursor_value=5)

    feed.process_new(handle)

    assert [c.args[0]["id"] for c in handle.call_args_list] == ["10", "20", "30"]
    assert cursor.get() == 30


def test_it_asks_only_for_mentions_after_the_cursor(tmp_path):
    feed, client, _, handle = build(tmp_path, [], cursor_value=629782824)

    feed.process_new(handle)

    assert client.calls == [{"types": ["mention"], "min_id": 629782824, "limit": 30}]


def test_the_cursor_advances_after_each_mention_not_after_the_batch(tmp_path):
    """A crash halfway through a batch must not repeat or skip what was already done."""
    feed, _, cursor, handle = build(tmp_path, [note(3), note(2), note(1)], cursor_value=0)
    seen = []
    handle.side_effect = lambda n: seen.append(cursor.get())

    feed.process_new(handle)

    assert seen == [0, 1, 2], "the cursor must trail the mention being handled by exactly one"
    assert cursor.get() == 3


def test_a_crash_mid_batch_leaves_the_cursor_at_the_last_handled_mention(tmp_path):
    feed, _, cursor, handle = build(tmp_path, [note(3), note(2), note(1)], cursor_value=0)
    handle.side_effect = [None, RuntimeError("boom"), None]

    with pytest.raises(RuntimeError):
        feed.process_new(handle)

    assert cursor.get() == 1, "the mention that crashed must be retried, the one before it must not"


def test_a_full_page_is_followed_by_another_fetch_straight_away(tmp_path):
    full = [note(i) for i in range(3, 0, -1)]
    feed, client, _, handle = build(tmp_path, full, [note(4)], cursor_value=0, page_size=3)

    feed.process_new(handle)

    assert client.calls[1]["min_id"] == 3
    assert handle.call_count == 4, "a backlog must be drained in one go, not one page per poll"


def test_a_partial_page_ends_the_poll(tmp_path):
    feed, client, _, handle = build(tmp_path, [note(1)], cursor_value=0, page_size=3)

    feed.process_new(handle)

    assert len(client.calls) == 1


def test_an_empty_page_changes_nothing(tmp_path):
    feed, _, cursor, handle = build(tmp_path, [], cursor_value=7)

    feed.process_new(handle)

    handle.assert_not_called()
    assert cursor.get() == 7
