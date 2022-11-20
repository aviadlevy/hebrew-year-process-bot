import asyncio
import functools
import os

import slack
from mastodon import Mastodon
from tweepy.asynchronous import AsyncClient

from async_stream_client_twitter import _AsyncStreamingClient
from src.stream_listener_mastodon import _StreamingListener

USER_ID = 1099727648471871490

BEARER_TOKEN = os.environ['BEARER_TOKEN']
CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
ACCESS_KEY = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']


def get_async_twitter_client():
    return AsyncClient(access_token=ACCESS_KEY, access_token_secret=ACCESS_SECRET,
                       consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET, wait_on_rate_limit=True)


def get_async_twitter_stream():
    return _AsyncStreamingClient(
        async_client=get_async_twitter_client(),
        slack_client=get_async_slack_client(),
        user_id=USER_ID,
        bearer_token=BEARER_TOKEN,
        wait_on_rate_limit=True)


def get_mastodon_stream_listener(mastodon_client):
    return _StreamingListener(mastodon_client=mastodon_client, slack_client=get_slack_client())


def get_slack_client() -> slack.WebClient:
    return slack.WebClient(os.environ['SLACK_API_TOKEN'])


def get_async_slack_client() -> slack.AsyncWebClient:
    return slack.AsyncWebClient(os.environ['SLACK_API_TOKEN'])


def get_mastodon_client():
    return Mastodon(access_token=os.environ['MASTODON_ACCESS_TOKEN'], api_base_url='https://botsin.space')


def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner
