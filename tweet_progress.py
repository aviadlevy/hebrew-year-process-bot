import traceback

from config import get_client, get_slack_client
from constant import PROGRESS_BAR_WIDTH, PROGRESS_SYMBOL, EMPTY_SYMBOL
from dates_helper import get_current_state
from progress_bar import ProgressBar
from tweet_helper import should_tweet, get_last_state


def get_progress_bar(current_state):
    return ProgressBar(width=PROGRESS_BAR_WIDTH, progress_symbol=PROGRESS_SYMBOL, empty_symbol=EMPTY_SYMBOL).update(
        current_state)


def send_slack_alert(sc, msg):
    sc.chat_postMessage(
        channel="#hebrew-year-process",
        text=msg
    )


def tweet():
    current_state = get_current_state()

    client = get_client()
    sc = get_slack_client()

    timeline = client.get_home_timeline()
    try:
        last_state = get_last_state(timeline.data)
    except Exception as e:
        send_slack_alert(sc, "exception: " + repr(e) + "\n" + traceback.format_exc())
        return -1
    is_tweeted = False
    if should_tweet(last_state, current_state):
        client.create_tweet(text=get_progress_bar(current_state))
        is_tweeted = True
    print("Finish running. tweeted? -> %s. last state -> %sø" % (is_tweeted, last_state))
    send_slack_alert(sc, "Finish running. tweeted? -> %s. last state -> %s" % (is_tweeted, last_state))
    return 0


if __name__ == '__main__':
    exit(tweet())
