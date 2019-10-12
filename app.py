import datetime
import os
import re
import traceback

import slack
import tweepy as tweepy
from flask import Flask, jsonify, request
from pyluach import dates, hebrewcal

from progress_bar import ProgressBar

PROGRESS_BAR_WIDTH = 20
EMPTY_SYMBOL = '░'
PROGRESS_SYMBOL = '▓'

sc = slack.WebClient(os.environ["SLACK_API_TOKEN"])
app = Flask(__name__)

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_KEY = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']
API_KEY = os.environ['API_KEY']


def get_current_state():
    today = dates.HebrewDate.today()
    days_count = 0
    total_days = 0
    # Tishrey and above
    if today.month >= 7:
        year = today.year
    else:
        year = today.year - 1
    # first from Tishrey to Adar
    for date in hebrewcal.Year(year).iterdates():
        if date.month == 1:
            break
        if date <= today:
            days_count += 1
        total_days += 1
    # then from Nissan to Elul
    for date in hebrewcal.Year(year + 1).iterdates():
        if date.month >= 7:
            continue
        if date <= today:
            days_count += 1
        total_days += 1
    return int((days_count / total_days) * 100)


def get_holiday(timeline):
    holiday = hebrewcal.holiday(dates.HebrewDate.today() + 1, israel=True)
    if holiday:
        if len([t for t in timeline
                if t.created_at == datetime.datetime.today() and t.text == "Happy %s" % holiday]) > 0:
            return None
    return holiday


def get_progress_bar(current_state):
    return ProgressBar(width=PROGRESS_BAR_WIDTH, progress_symbol=PROGRESS_SYMBOL, empty_symbol=EMPTY_SYMBOL).update(
        current_state)


def get_last_state(tweets):
    for tweet in tweets:
        match = re.match(r'^[%s%s]{%d}\s(\d+)' % (EMPTY_SYMBOL, PROGRESS_SYMBOL, PROGRESS_BAR_WIDTH) + "%$", tweet.text)
        if match:
            return int(match.group(1))


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
    if last_state is None or current_state > last_state or (last_state == 100 and current_state == 0):
        api.update_status(status=get_progress_bar(current_state))
        is_tweeted = True
    holiday = get_holiday(timeline)
    if holiday:
        api.update_status(status="Happy %s" % holiday)
    send_slack_alert(
        "Finish running. tweeted? -> %s. last state -> %s holiday -> %s" % (is_tweeted, last_state, holiday))
    return jsonify(success=True, tweeted=is_tweeted, last_state=last_state, holiday=holiday is not None)


if __name__ == '__main__':
    app.run(os.environ['PORT'])
