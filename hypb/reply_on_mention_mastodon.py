import logging
import sys
import traceback

from hypb.config import get_mastodon_client, get_mastodon_stream_listener
from hypb.settings import REQUIRED_REPLIER_VARS, ConfigurationError, require
from hypb.utils import send_alert

logger = logging.getLogger(__name__)


def reply():
    mastodon_client = get_mastodon_client()
    stream = get_mastodon_stream_listener(mastodon_client=mastodon_client)
    logger.info("listening for mentions")
    mastodon_client.stream_user(stream)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        require(REQUIRED_REPLIER_VARS)
    except ConfigurationError as e:
        logger.error("%s", e)
        return 2

    try:
        reply()
    except Exception as e:
        logger.exception("replier stopped")
        send_alert("exception: " + repr(e) + "\n" + traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
