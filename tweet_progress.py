import os
import traceback

import slack
import tweepy as tweepy

from constant import PROGRESS_BAR_WIDTH, PROGRESS_SYMBOL, EMPTY_SYMBOL
from dates_helper import get_current_state
from progress_bar import ProgressBar
from tweet_helper import should_tweet, get_last_state

sc = slack.WebClient(os.environ['SLACK_API_TOKEN'])

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_KEY = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']


def get_progress_bar(current_state):
    return ProgressBar(width=PROGRESS_BAR_WIDTH, progress_symbol=PROGRESS_SYMBOL, empty_symbol=EMPTY_SYMBOL).update(
        current_state)


def send_slack_alert(msg):
    sc.chat_postMessage(
        channel="#hebrew-year-process",
        text=msg
    )


def tweet():
    current_state = get_current_state()

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

    api = tweepy.API(auth)
    timeline = api.user_timeline()
    try:
        last_state = get_last_state(timeline)
    except Exception as e:
        send_slack_alert("exception: " + repr(e) + "\n" + traceback.format_exc())
        return -1
    is_tweeted = False
    if should_tweet(last_state, current_state):
        api.update_status(status=get_progress_bar(current_state))
        is_tweeted = True
    print("Finish running. tweeted? -> %s. last state -> %sø" % (is_tweeted, last_state))
    send_slack_alert(
        "Finish running. tweeted? -> %s. last state -> %s" % (is_tweeted, last_state))
    return 0


if __name__ == '__main__':
    exit(tweet())
