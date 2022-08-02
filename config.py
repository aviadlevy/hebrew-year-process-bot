import os

import slack
from tweepy.asynchronous import AsyncClient

from async_stream_client import _AsyncStreamingClient

USER_ID = 1099727648471871490

BEARER_TOKEN = os.environ['BEARER_TOKEN']
CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_KEY = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']


def get_async_client():
    return AsyncClient(access_token=ACCESS_KEY, access_token_secret=ACCESS_SECRET,
                       consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET, wait_on_rate_limit=True)


def get_async_stream():
    return _AsyncStreamingClient(
        async_client=get_async_client(),
        user_id=USER_ID,
        bearer_token=BEARER_TOKEN,
        wait_on_rate_limit=True)


def get_async_slack_client():
    return slack.AsyncWebClient(os.environ['SLACK_API_TOKEN'])
