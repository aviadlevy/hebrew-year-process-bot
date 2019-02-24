import os
import re

import tweepy as tweepy
from flask import Flask, jsonify
from pyluach import dates, hebrewcal

from app.progress_bar import ProgressBar

app = Flask(__name__)

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_KEY = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']


def get_current_state():
    today = dates.HebrewDate.today()
    days_count = 0
    total_days = 0
    if today.month >= 7:  # Tishrey and above
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


def get_progress_bar(current_state):
    return ProgressBar().update(current_state)


def get_last_state(text):
    return int(re.findall(r'\d+', text)[0])


@app.route('/tweet')
def tweet():
    current_state = get_current_state()

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

    api = tweepy.API(auth)
    last_state = None
    try:
        last_state = get_last_state(api.home_timeline()[0].text)
    except IndexError:
        pass
    except Exception as e:
        # error. log
        pass
    is_tweeted = False
    if last_state is None or current_state > last_state:
        api.update_status(status=get_progress_bar(current_state))
        is_tweeted = True
    return jsonify(success=True, tweeted=is_tweeted)


if __name__ == '__main__':
    app.run(os.environ['PORT'])
