"""The mentions Mastodon holds that the replier has not dealt with yet.

The replier used to read mentions from the streaming API, which delivers them
only while connected and replays nothing after a drop. mastodon.social cuts
every stream after about 15 seconds, so a mention that arrived in the wrong
second was lost for good. Here Mastodon is the source of truth: the cursor says
how far we have got, and whatever is newer is handled once, in order, whenever
we next ask.
"""

import logging
from collections.abc import Callable

from mastodon import Mastodon

from hypb.mention_cursor import MentionCursor

logger = logging.getLogger(__name__)

PAGE_SIZE = 30

#: Cursor value meaning "no mention existed yet", so the first one ever
#: received is answered rather than mistaken for history.
EMPTY_ACCOUNT_CURSOR = 0


class MentionFeed:
    """Hands each new mention to a handler exactly once, oldest first."""

    def __init__(self, mastodon_client: Mastodon, cursor: MentionCursor, page_size: int = PAGE_SIZE):
        self._client = mastodon_client
        self._cursor = cursor
        self._page_size = page_size

    def process_new(self, handle: Callable[[dict], None]) -> None:
        """Handle every mention newer than the cursor, advancing it after each one.

        The cursor moves per mention, not per batch, so a crash halfway through
        neither repeats nor skips what was already done.
        """
        cursor = self._cursor.get()
        if cursor is None:
            self._start_from_the_newest_mention()
            return

        while True:
            page = self._client.notifications(types=["mention"], min_id=cursor, limit=self._page_size)
            # Mastodon returns a page newest-first; answer the oldest question first.
            for notification in sorted(page, key=lambda n: int(n["id"])):
                handle(notification)
                cursor = int(notification["id"])
                self._cursor.set(cursor)
            if len(page) < self._page_size:
                return

    def _start_from_the_newest_mention(self) -> None:
        """Record where history ends without answering any of it.

        A deploy must not re-answer mentions the stream already handled, and the
        very first run has no way to know which those were.
        """
        newest_page = self._client.notifications(types=["mention"], limit=1)
        newest = max((int(n["id"]) for n in newest_page), default=EMPTY_ACCOUNT_CURSOR)
        self._cursor.set(newest)
        logger.info("no mention cursor yet; starting after notification id=%s", newest)
