import asyncio
import functools
import os

from mastodon import Mastodon
from tweepy.asynchronous import AsyncClient

from src.async_stream_client_twitter import _AsyncStreamingClient
from src.stream_listener_mastodon import _StreamingListener

USER_ID = 1099727648471871490


def get_async_twitter_client():
    return AsyncClient(access_token=os.environ["ACCESS_KEY"], access_token_secret=os.environ["ACCESS_SECRET"],
                       consumer_key=os.environ["CONSUMER_KEY"], consumer_secret=os.environ["CONSUMER_SECRET"],
                       wait_on_rate_limit=True)


def get_async_twitter_stream():
    return _AsyncStreamingClient(
        async_client=get_async_twitter_client(),
        user_id=USER_ID,
        bearer_token=os.environ["BEARER_TOKEN"],
        wait_on_rate_limit=True)


def get_mastodon_stream_listener(mastodon_client):
    return _StreamingListener(mastodon_client=mastodon_client)


def get_mastodon_client():
    return Mastodon(access_token=os.environ["MASTODON_ACCESS_TOKEN"], api_base_url="https://botsin.space")


def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner
