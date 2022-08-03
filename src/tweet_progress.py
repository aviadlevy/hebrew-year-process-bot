import asyncio
import traceback

from config import get_async_client, get_async_slack_client, USER_ID
from utils import send_slack_alert
from constant import PROGRESS_BAR_WIDTH, PROGRESS_SYMBOL, EMPTY_SYMBOL
from dates_helper import get_current_state
from progress_bar import ProgressBar
from tweet_helper import should_tweet, get_last_state


def get_progress_bar(current_state):
    return ProgressBar(width=PROGRESS_BAR_WIDTH, progress_symbol=PROGRESS_SYMBOL, empty_symbol=EMPTY_SYMBOL).update(
        current_state)


async def tweet():
    current_state = get_current_state()

    client = get_async_client()
    sc = get_async_slack_client()

    timeline = await client.get_users_tweets(id=USER_ID, user_auth=True)
    try:
        last_state = get_last_state(timeline.data)
    except Exception as e:
        await send_slack_alert(sc, "exception: " + repr(e) + "\n" + traceback.format_exc())
        return -1
    is_tweeted = False
    if should_tweet(last_state, current_state):
        await client.create_tweet(text=get_progress_bar(current_state))
        is_tweeted = True
    print("Finish running. tweeted? -> %s. last state -> %sø" % (is_tweeted, last_state))
    await send_slack_alert(sc, "Finish running. tweeted? -> %s. last state -> %s" % (is_tweeted, last_state))
    return 0


if __name__ == '__main__':
    exit(asyncio.run(tweet()))
