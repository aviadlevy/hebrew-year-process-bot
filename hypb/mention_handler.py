"""What the replier does with one mention: answer it, leave it, or give up on it.

The poller owns *when* a mention is looked at; this owns *what happens* to it.
Every mention ends in exactly one outcome, and every outcome is reported to
Telegram, so the person running the bot sees what was asked and what the bot
made of it.
"""

import logging
import traceback
from collections.abc import Callable
from datetime import datetime, timedelta

from mastodon import Mastodon

from hypb.mention_notice import build_mention_notice, truncate
from hypb.tweet_helper import get_text_to_reply

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now().astimezone()


class MentionHandler:
    """Replies to a mention if it is fresh and asks something the bot knows."""

    def __init__(
        self,
        mastodon_client: Mastodon,
        notify: Callable[[str], bool],
        *,
        max_age: timedelta,
        now: Callable[[], datetime] = _utcnow,
    ):
        self._client = mastodon_client
        self._notify = notify
        self._max_age = max_age
        self._now = now

    def handle(self, notification) -> None:
        """Deal with one mention. Never raises: a failure is alerted, not propagated.

        The poller moves its cursor past this notification either way, so a
        mention that cannot be answered is reported once rather than retried
        forever in front of the ones behind it.
        """
        status = notification.get("status") or {}
        account = notification.get("account") or {}
        content = status.get("content") or ""
        logger.info(
            "mention id=%s status_id=%s from=@%s language=%s visibility=%s content=%r",
            notification.get("id"),
            status.get("id"),
            account.get("acct"),
            status.get("language"),
            status.get("visibility"),
            truncate(content),
        )

        outcome = self._decide_and_reply(notification, status, content)
        # After handling, so the notice carries the outcome. The notifier reports
        # failure by returning False rather than raising, so it cannot undo a reply.
        self._notify(build_mention_notice(notification, outcome))

    def _decide_and_reply(self, notification, status, content: str) -> str:
        age = self._now() - notification["created_at"]
        if age > self._max_age:
            logger.info("mention id=%s is too old (%s); not replying", notification.get("id"), age)
            return f"skipped, {int(age.total_seconds() // 60)} min old"

        try:
            reply = get_text_to_reply(content.lower())
            if not reply:
                logger.info("no keyword matched in status_id=%s; not replying", status.get("id"))
                return "not replied (no keyword matched)"
            logger.info("replying to status_id=%s with %r", status.get("id"), truncate(reply))
            posted = self._client.status_reply(
                to_status=notification["status"],
                status=reply,
                idempotency_key=f"hypb-mention-{notification['id']}",
            )
        except Exception as e:
            logger.exception("failed to handle mention id=%s status_id=%s", notification.get("id"), status.get("id"))
            self._notify("exception: " + repr(e) + "\n" + traceback.format_exc())
            return f"failed: {e!r}"

        logger.info("replied to status_id=%s; reply status_id=%s", status.get("id"), (posted or {}).get("id"))
        return "replied"
