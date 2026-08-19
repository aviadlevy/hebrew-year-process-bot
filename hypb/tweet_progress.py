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
    already went out. Returns None when the window genuinely holds no progress
    toot, in which case the caller records without posting -- that is D3's
    intended, conservative outcome.

    A fetch failure is a different situation and is *not* caught here: it
    propagates so the caller can tell "no progress toot in the window" apart
    from "we could not check", and abort without writing state on the latter.
    """
    timeline = await account_statuses(mastodon_client, limit=SEED_TIMELINE_LIMIT)
    return get_last_state(timeline)


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

    # One timeline read at most, and only when some platform has no row. A
    # fetch failure here is not the same as an empty window: it means we do
    # not actually know the seed, so the run aborts without writing any row
    # rather than recording a percentage that may already be stale or, worse,
    # was never posted at all.
    seed = None
    if any(store.get(platform) is None for platform in PLATFORMS):
        try:
            seed = await _seed_from_timeline(mastodon_client)
        except Exception as e:
            logger.exception("could not seed from the mastodon timeline; aborting without writing state")
            await send_async_alert("could not seed from the mastodon timeline: " + repr(e) + "\n" + traceback.format_exc())
            return 1

    outcomes = {}
    for platform in PLATFORMS:
        # store.get/store.set are blocking SQLite calls made directly here,
        # unlike the run_in_executor wrapper used for the Mastodon calls above.
        # That is fine: this is a one-shot process with no other tasks running
        # concurrently, the database is on local disk, and each call is
        # sub-millisecond -- there is nothing for blocking the event loop to
        # starve.
        stored_state = store.get(platform)
        last_state = seed if stored_state is None else stored_state

        if stored_state is None and last_state is not None:
            # A seed recovered from the timeline is recorded, not merely used.
            # Without this the row stays absent until the first post, so every
            # run in between re-reads Mastodon -- leaving the bot coupled to the
            # markup this store exists to stop depending on, and leaving nothing
            # for a restart to recover from.
            store.set(platform, last_state)

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

    try:
        # Telegram is this job's only observability -- a crash that reaches
        # here (StateStore() unable to open its file, a disk full mid-write)
        # must still page, not escape asyncio.run as a bare traceback that
        # only journald ever sees.
        return asyncio.run(tweet())
    except Exception as e:
        logger.exception("tweet_progress failed")
        # The loop asyncio.run() used has already closed, so a fresh one is
        # spun up just to send the alert.
        asyncio.run(send_async_alert("tweet_progress failed: " + repr(e) + "\n" + traceback.format_exc()))
        return 1


if __name__ == "__main__":
    sys.exit(main())
