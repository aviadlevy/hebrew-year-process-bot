import os
import traceback

import slack
import tweepy as tweepy
from flask import Flask, jsonify, request

from constant import PROGRESS_BAR_WIDTH, PROGRESS_SYMBOL, EMPTY_SYMBOL
from dates_helper import get_current_state, get_holiday
from progress_bar import ProgressBar
from tweet_helper import is_holiday_tweeted_today, should_tweet, get_last_state

sc = slack.WebClient(os.environ['SLACK_API_TOKEN'])
app = Flask(__name__)

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_KEY = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']
API_KEY = os.environ['API_KEY']


def get_progress_bar(current_state):
    return ProgressBar(width=PROGRESS_BAR_WIDTH, progress_symbol=PROGRESS_SYMBOL, empty_symbol=EMPTY_SYMBOL).update(
        current_state)


def send_slack_alert(msg):
    sc.chat_postMessage(
        channel="#hebrew-year-process",
        text=msg
    )


@app.route('/tweet')
def tweet():
    if not ("apikey" in request.args and request.args.get("apikey") == API_KEY):
        send_slack_alert("invalid client")
        return "Invalid Client", 401
    current_state = get_current_state()

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

    api = tweepy.API(auth)
    timeline = api.user_timeline()
    try:
        last_state = get_last_state(timeline)
    except Exception as e:
        send_slack_alert("exception: " + repr(e) + "\n" + traceback.format_exc())
        return jsonify(success=False, tweeted=False), 500
    is_tweeted = False
    if should_tweet(last_state, current_state):
        api.update_status(status=get_progress_bar(current_state))
        is_tweeted = True
    holiday = get_holiday()
    if holiday and not is_holiday_tweeted_today(timeline, holiday):
        api.update_status(status="Happy %s!" % holiday)
    send_slack_alert(
        "Finish running. tweeted? -> %s. last state -> %s holiday -> %s" % (is_tweeted, last_state, holiday))
    return jsonify(success=True, tweeted=is_tweeted, last_state=last_state, holiday=holiday is not None)


if __name__ == '__main__':
    app.run(os.environ['PORT'])
