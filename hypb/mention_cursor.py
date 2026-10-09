"""Durable memory of the newest mention the replier has dealt with.

The replier polls for mentions newer than this id, so it has to outlive the
process: lose it and a restart either re-answers history or skips whatever
arrived while the container was down. It lives in the database the progress job
already keeps on the state volume, in its own table.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from hypb.state_store import DEFAULT_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mention_cursor (
    id                   INTEGER PRIMARY KEY CHECK (id = 1),
    last_notification_id INTEGER NOT NULL
)
"""


class MentionCursor:
    """The id of the newest mention notification already handled."""

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

    def get(self) -> int | None:
        """The newest handled notification id, or None if nothing was ever handled."""
        with self._connect() as conn:
            row = conn.execute("SELECT last_notification_id FROM mention_cursor WHERE id = 1").fetchone()
        return None if row is None else row[0]

    def set(self, notification_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO mention_cursor (id, last_notification_id) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET last_notification_id = excluded.last_notification_id",
                (notification_id,),
            )
