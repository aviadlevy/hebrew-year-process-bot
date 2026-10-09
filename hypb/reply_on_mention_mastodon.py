import logging
import os
import sys
from datetime import timedelta

from hypb.alert_messages import error_alert
from hypb.config import get_mastodon_client
from hypb.mention_cursor import MentionCursor
from hypb.mention_feed import MentionFeed
from hypb.mention_handler import MentionHandler
from hypb.mention_poller import POLL_INTERVAL_SECONDS, MentionPoller, PollPolicy
from hypb.settings import (
    REQUIRED_REPLIER_VARS,
    ConfigurationError,
    positive_number,
    require,
)
from hypb.startup import build_startup_message
from hypb.utils import send_alert

logger = logging.getLogger(__name__)

#: A mention older than this is reported but not answered, so a long outage does
#: not end with the bot replying to questions nobody is waiting on any more.
DEFAULT_MENTION_MAX_AGE_MINUTES = 30.0


def reply(max_age: timedelta, poll_interval_seconds: float):
    mastodon_client = get_mastodon_client()
    handler = MentionHandler(mastodon_client, send_alert, max_age=max_age)
    feed = MentionFeed(mastodon_client, MentionCursor())
    poller = MentionPoller(
        lambda: feed.process_new(handler.handle),
        send_alert,
        policy=PollPolicy(interval_seconds=poll_interval_seconds),
    )
    logger.info("polling for mentions every %.0fs; answering none older than %s", poll_interval_seconds, max_age)
    # Polling replaced the streaming API: mastodon.social cuts every stream after
    # ~15s and replays nothing, so a mention arriving in the wrong second was
    # lost. A transport failure is retried in place; anything else escapes.
    poller.run()


def main() -> int:
    # LOG_LEVEL=DEBUG turns on verbose logging without a code change, so
    # `docker logs` can be made verbose on demand. A
    # typo must not stop the replier from answering mentions, so it falls back
    # to INFO and says so.
    requested_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = requested_level if requested_level in logging.getLevelNamesMapping() else "INFO"
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if level != requested_level:
        logger.warning("unknown LOG_LEVEL %r; falling back to INFO", requested_level)

    # urllib3 logs every request line at DEBUG, and the Telegram bot token is
    # part of that URL ("POST /bot<TOKEN>/sendMessage"). LOG_LEVEL=DEBUG is for
    # seeing our own events, never for publishing a secret to the
    # container log, so the HTTP libraries stay at INFO whatever we run at.
    logging.getLogger("urllib3").setLevel(logging.INFO)
    try:
        require(REQUIRED_REPLIER_VARS)
        max_age = timedelta(minutes=positive_number("MENTION_MAX_AGE_MINUTES", DEFAULT_MENTION_MAX_AGE_MINUTES))
        poll_interval_seconds = positive_number("POLL_INTERVAL_SECONDS", POLL_INTERVAL_SECONDS)
    except ConfigurationError as e:
        logger.error("%s", e)
        return 2

    # Sent before polling starts, so a broken alerting path shows up on the
    # deploy rather than during the first incident. It is not fatal: the replier
    # answering mentions matters more than it being able to page anyone.
    if not send_alert(build_startup_message()):
        logger.error("telegram alerting is not working; the replier will run but nothing will page you")

    try:
        # reply() only returns by raising: the poller loops forever, so anything
        # reaching here is a failure it deliberately would not retry.
        reply(max_age, poll_interval_seconds)
    except Exception as e:
        logger.exception("replier stopped")
        send_alert(error_alert("Replier crashed", e))
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
