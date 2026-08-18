import logging
import sys
import traceback

from hypb.config import get_mastodon_client, get_mastodon_stream_listener
from hypb.settings import REQUIRED_REPLIER_VARS, ConfigurationError, require
from hypb.startup import build_startup_message
from hypb.stream_supervisor import StreamSupervisor
from hypb.utils import send_alert

logger = logging.getLogger(__name__)


def reply():
    mastodon_client = get_mastodon_client()
    stream = get_mastodon_stream_listener(mastodon_client=mastodon_client)
    logger.info("listening for mentions")
    # Neither a dropped nor a cleanly-closed stream is worth ending the process
    # over: mastodon.social recycles long-lived connections routinely, and a
    # container restart per recycle loses every mention that arrives while it is
    # down. The supervisor reconnects in place and pages only if it cannot.
    StreamSupervisor(run_stream=lambda: mastodon_client.stream_user(stream), alert=send_alert).run()


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

    # Sent before streaming starts, so a broken alerting path shows up on the
    # deploy rather than during the first incident. It is not fatal: the replier
    # answering mentions matters more than it being able to page anyone.
    if not send_alert(build_startup_message()):
        logger.error("telegram alerting is not working; the replier will run but nothing will page you")

    try:
        # reply() only returns by raising: the supervisor loops forever, so
        # anything reaching here is a failure it deliberately would not retry.
        reply()
    except Exception as e:
        logger.exception("replier stopped")
        send_alert("exception: " + repr(e) + "\n" + traceback.format_exc())
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
