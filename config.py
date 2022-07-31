import os

import slack
import tweepy as tweepy

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_KEY = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']


def get_client():
    client = tweepy.Client(access_token=ACCESS_KEY, access_token_secret=ACCESS_SECRET,
                           consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET, wait_on_rate_limit=True)
    return client


def get_slack_client():
    return slack.WebClient(os.environ['SLACK_API_TOKEN'])
