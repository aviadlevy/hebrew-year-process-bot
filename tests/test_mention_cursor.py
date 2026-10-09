"""The cursor is what lets the poller pick up exactly where it left off.

Lose it and the replier either re-answers history or skips whatever arrived while
it was down, so it has to survive a restart and live in the same database the
progress job already uses.
"""

from hypb.mention_cursor import MentionCursor
from hypb.state_store import MASTODON, StateStore


def test_a_fresh_database_has_no_cursor(tmp_path):
    assert MentionCursor(tmp_path / "state.db").get() is None


def test_the_cursor_round_trips(tmp_path):
    cursor = MentionCursor(tmp_path / "state.db")

    cursor.set(629782824)

    assert cursor.get() == 629782824


def test_setting_again_overwrites_rather_than_adds(tmp_path):
    cursor = MentionCursor(tmp_path / "state.db")

    cursor.set(1)
    cursor.set(2)

    assert cursor.get() == 2


def test_the_cursor_survives_a_restart(tmp_path):
    MentionCursor(tmp_path / "state.db").set(42)

    assert MentionCursor(tmp_path / "state.db").get() == 42


def test_the_path_comes_from_state_db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB_PATH", str(tmp_path / "from_env.db"))

    MentionCursor().set(7)

    assert (tmp_path / "from_env.db").exists()


def test_it_shares_a_database_with_the_progress_state(tmp_path):
    """One volume, one file: the cursor must not clobber the post state's table."""
    StateStore(tmp_path / "state.db").set(MASTODON, 50)
    MentionCursor(tmp_path / "state.db").set(9)

    assert StateStore(tmp_path / "state.db").get(MASTODON) == 50
    assert MentionCursor(tmp_path / "state.db").get() == 9
