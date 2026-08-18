"""Durable memory of the last percentage published to each platform.

The bot used to recover this by fetching its own last 50 Mastodon statuses and
regexing the number back out of the rendered HTML. That coupled posting to
Mastodon's availability and its exact markup, and -- because a no-match
returned None rather than raising -- fed None into an integer comparison and
crashed the run with a TypeError.

State is keyed by platform because Twitter and Mastodon fail independently. A
single shared number forces a bad choice the first time one succeeds and the
other does not: advance it and the failed platform skips that percentage
forever; hold it back and the platform that already posted repeats itself.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

MASTODON = "mastodon"
TWITTER = "twitter"
PLATFORMS = (MASTODON, TWITTER)

DEFAULT_DB_PATH = "/var/lib/hypb/state.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS post_state (
    platform   TEXT PRIMARY KEY,
    last_state INTEGER NOT NULL
)
"""


class StateStore:
    """The last percentage successfully published, per platform."""

    def __init__(self, db_path: str | os.PathLike[str] | None = None):
        self._db_path = Path(db_path or os.getenv("STATE_DB_PATH") or DEFAULT_DB_PATH)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    @contextmanager
    def _connect(self):
        # sqlite3.Connection used as a context manager commits or rolls back --
        # it does not close. Both are wanted, so the close is explicit.
        conn = sqlite3.connect(self._db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def get(self, platform: str) -> int | None:
        """The last percentage published to `platform`, or None if never."""
        with self._connect() as conn:
            row = conn.execute("SELECT last_state FROM post_state WHERE platform = ?", (platform,)).fetchone()
        return None if row is None else row[0]

    def set(self, platform: str, last_state: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO post_state (platform, last_state) VALUES (?, ?) "
                "ON CONFLICT(platform) DO UPDATE SET last_state = excluded.last_state",
                (platform, last_state),
            )
