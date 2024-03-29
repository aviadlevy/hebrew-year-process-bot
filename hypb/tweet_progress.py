import asyncio
import sys
import traceback

from config import get_async_twitter_client, get_mastodon_client, run_in_executor
from constant import EMPTY_SYMBOL, PROGRESS_BAR_WIDTH, PROGRESS_SYMBOL
from dates_helper import get_current_state
from progress_bar import ProgressBar
from tweet_helper import get_last_state, should_tweet
from utils import send_async_alert


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
def timeline_home(mastodon_client, limit=None):
    """
    wrapper of asyncio to blocking library

    :param limit: limit timeline results
    :param mastodon_client: blocking client of mastodon
    :return:
    """
    return mastodon_client.timeline_home(limit=limit)


def get_progress_bar(current_state):
    return ProgressBar(width=PROGRESS_BAR_WIDTH, progress_symbol=PROGRESS_SYMBOL, empty_symbol=EMPTY_SYMBOL).update(
        current_state)


async def tweet():
    current_state = get_current_state()

    twitter_client = get_async_twitter_client()
    mastodon_client = get_mastodon_client()

    timeline = await timeline_home(mastodon_client, limit=10)
    try:
        last_state = get_last_state(timeline)
    except Exception as e:
        await send_async_alert("exception: " + repr(e) + "\n" + traceback.format_exc())
        return -1
    is_tweeted = False
    if should_tweet(last_state, current_state):
        progress_bar = get_progress_bar(current_state)
        await twitter_client.create_tweet(text=progress_bar)
        await toot(mastodon_client, progress_bar)
        is_tweeted = True
    print(f"tweeted? -> {is_tweeted}. current state -> {current_state} .last state -> {last_state}ø")
    await send_async_alert(f"tweeted? -> {is_tweeted}. current state -> {current_state} .last state -> {last_state}ø")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(tweet()))
