import os

import slack
from tweepy.asynchronous import AsyncClient

BEARER_TOKEN = os.environ['BEARER_TOKEN']


def get_async_client():
    return AsyncClient(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)


def get_async_slack_client():
    return slack.AsyncWebClient(os.environ['SLACK_API_TOKEN'])
