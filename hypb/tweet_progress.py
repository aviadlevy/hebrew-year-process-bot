import asyncio
import logging
import sys
import traceback

from hypb.config import get_async_twitter_client, get_mastodon_client, run_in_executor
from hypb.constant import (
    EMPTY_SYMBOL,
    MASTODON_USER_ID,
    PROGRESS_BAR_WIDTH,
    PROGRESS_SYMBOL,
)
from hypb.dates_helper import get_current_state
from hypb.progress_bar import ProgressBar
from hypb.settings import REQUIRED_PROGRESS_VARS, ConfigurationError, require
from hypb.state_store import MASTODON, PLATFORMS, TWITTER, StateStore
from hypb.tweet_helper import get_last_state, should_tweet
from hypb.utils import send_async_alert

logger = logging.getLogger(__name__)

SEED_TIMELINE_LIMIT = 50


@run_in_executor
def toot(mastodon_client, text):
    """
    wrapper of asyncio to blocking library

    :param mastodon_client: blocking client of mastodon
    :param text: text to toot
    :return:
    """
    return mastodon_client.toot(text)


@run_in_executor
def account_statuses(mastodon_client, limit=None):
    """
    wrapper of asyncio to blocking library

    :param limit: limit timeline results
    :param mastodon_client: blocking client of mastodon
    :return:
    """
    return mastodon_client.account_statuses(id=MASTODON_USER_ID, limit=limit)


def get_progress_bar(current_state):
    return ProgressBar(width=PROGRESS_BAR_WIDTH, progress_symbol=PROGRESS_SYMBOL, empty_symbol=EMPTY_SYMBOL).update(current_state)


async def _seed_from_timeline(mastodon_client):
    """The last published percentage as Mastodon still remembers it.

    Consulted only for a platform with no stored row: it is how a first run --
    or one after the volume was lost -- avoids re-posting a percentage that
    already went out. Returns None when the window holds no progress toot, in
    which case the caller records without posting.
    """
    try:
        timeline = await account_statuses(mastodon_client, limit=SEED_TIMELINE_LIMIT)
        return get_last_state(timeline)
    except Exception as e:
        logger.exception("could not seed from the mastodon timeline")
        await send_async_alert("could not seed from the mastodon timeline: " + repr(e) + "\n" + traceback.format_exc())
        return None


async def _publish(platform, poster, progress_bar):
    """Post the bar, reporting whether it landed. Never raises.

    One platform's outage must not stop the other from being tried, so the
    exception is turned into a return value here rather than unwinding tweet().
    """
    try:
        await poster(progress_bar)
    except Exception as e:
        logger.exception("posting to %s failed", platform)
        await send_async_alert(f"posting to {platform} failed: " + repr(e) + "\n" + traceback.format_exc())
        return False
    return True


async def tweet():
    current_state = get_current_state()
    store = StateStore()
    mastodon_client = get_mastodon_client()
    twitter_client = get_async_twitter_client()

    posters = {
        MASTODON: lambda text: toot(mastodon_client, text),
        TWITTER: lambda text: twitter_client.create_tweet(text=text),
    }

    # One timeline read at most, and only when some platform has no row.
    seed = None
    if any(store.get(platform) is None for platform in PLATFORMS):
        seed = await _seed_from_timeline(mastodon_client)

    outcomes = {}
    for platform in PLATFORMS:
        last_state = store.get(platform)
        if last_state is None:
            last_state = seed

        if last_state is None:
            # Nothing to compare against and no way to learn it.
            store.set(platform, current_state)
            outcomes[platform] = "seeded"
        elif not should_tweet(last_state, current_state):
            outcomes[platform] = "skipped"
        elif await _publish(platform, posters[platform], get_progress_bar(current_state)):
            # Recorded only after the post lands, so a failure is retried on
            # the next run instead of silently skipping this percentage.
            store.set(platform, current_state)
            outcomes[platform] = "posted"
        else:
            outcomes[platform] = "failed"

    summary = ", ".join(f"{platform}: {outcome}" for platform, outcome in outcomes.items())
    logger.info("current state -> %s. %s", current_state, summary)
    await send_async_alert(f"current state -> {current_state}. {summary}")
    return 1 if "failed" in outcomes.values() else 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        require(REQUIRED_PROGRESS_VARS)
    except ConfigurationError as e:
        logger.error("%s", e)
        return 2
    return asyncio.run(tweet())


if __name__ == "__main__":
    sys.exit(main())
