import logging
import traceback
from collections.abc import Callable

from mastodon import Mastodon, StreamListener

from hypb.mention_notice import build_mention_notice
from hypb.tweet_helper import get_text_to_reply
from hypb.utils import send_alert

logger = logging.getLogger(__name__)

#: Toot bodies are arbitrary user input and arrive as HTML; a long one would
#: bury the rest of the log line for no extra diagnostic value.
MAX_LOGGED_CONTENT_CHARS = 500


def _truncate(text: str) -> str:
    if len(text) <= MAX_LOGGED_CONTENT_CHARS:
        return text
    return text[:MAX_LOGGED_CONTENT_CHARS] + f"... [{len(text) - MAX_LOGGED_CONTENT_CHARS} more chars]"


class _StreamingListener(StreamListener):
    """Extends AsyncStreamingClient to accept function, to be invoked for every new tweet"""

    def __init__(self, mastodon_client: Mastodon, *args, notify: Callable[[str], bool] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.mastodon_client = mastodon_client
        self._notify = notify if notify is not None else send_alert

    def on_any_event(self, name, data=None, for_stream=None):
        """Per-event proof of life at DEBUG, so LOG_LEVEL=DEBUG shows what the stream delivers."""
        logger.debug("stream event: %s", name)

    def handle_heartbeat(self):
        """Proof the connection is alive, at DEBUG so it cannot flood the log."""
        logger.debug("stream heartbeat")

    def on_notification(self, notification):
        notification_type = notification.get("type")
        if notification_type != "mention":
            logger.info("ignoring notification id=%s type=%s", notification.get("id"), notification_type)
            return None

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
            _truncate(content),
        )

        posted = None
        try:
            reply = get_text_to_reply(content.lower())
            if not reply:
                logger.info("no keyword matched in status_id=%s; not replying", status.get("id"))
                outcome = "not replied (no keyword matched)"
            else:
                logger.info("replying to status_id=%s with %r", status.get("id"), _truncate(reply))
                posted = self.reply_to_toot(notification, reply)
                logger.info("replied to status_id=%s; reply status_id=%s", status.get("id"), (posted or {}).get("id"))
                outcome = "replied"
        except Exception as e:
            logger.exception("failed to handle mention id=%s status_id=%s", notification.get("id"), status.get("id"))
            send_alert("exception: " + repr(e) + "\n" + traceback.format_exc())
            outcome = f"failed: {e!r}"

        # After handling, so the notice carries the outcome. The notifier reports
        # failure by returning False rather than raising, so it cannot undo a reply.
        self._notify(build_mention_notice(notification, outcome))
        return posted

    def reply_to_toot(self, notification, message: str):
        return self.mastodon_client.status_reply(to_status=notification.status, status=message)
