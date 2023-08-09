import random

import pytest
import slack
from tweepy import Tweet
from tweepy.asynchronous import AsyncClient

from src.async_stream_client_twitter import _AsyncStreamingClient
from src.dates_helper import get_current_date, get_current_parashah


def create_tweet(message, tweet_id, user_id=None):
    return Tweet({
        "text": message,
        "id": tweet_id,
        "author_id": user_id
    })


async def base_flow(mocker, message, user_id, tweet_user_id):
    async_client: AsyncClient = AsyncClient()
    mocker.patch.object(async_client, "create_tweet")
    spy = mocker.spy(async_client, "create_tweet")
    slack_client: slack.AsyncWebClient = slack.AsyncWebClient()
    spy_slack = mocker.patch.object(slack_client, "chat_postMessage")
    stream_client = _AsyncStreamingClient(async_client, slack_client, user_id, bearer_token="token")
    tweet_id = random.randint(0, 100)
    await stream_client.on_tweet(create_tweet(message, tweet_id, tweet_user_id))
    return spy, spy_slack, tweet_id


@pytest.mark.asyncio
async def test_date(mocker):
    spy, spy_slack, tweet_id = await base_flow(mocker, "What's the date?", 1234, 4567)
    spy.assert_called_once_with(in_reply_to_tweet_id=tweet_id, text=f"The date is:\n{get_current_date(lang='eng')}")
    spy_slack.assert_not_called()


@pytest.mark.asyncio
async def test_date_heb(mocker):
    spy, spy_slack, tweet_id = await base_flow(mocker, "מה התאריך?", 1234, 4567)
    spy.assert_called_once_with(in_reply_to_tweet_id=tweet_id, text=f"התאריך הוא:\n{get_current_date(lang='heb')}")
    spy_slack.assert_not_called()


@pytest.mark.asyncio
async def test_date_when_bot_tweeted(mocker):
    spy, spy_slack, tweet_id = await base_flow(mocker, "What's the date?", 1234, 1234)
    spy.assert_not_called()
    spy_slack.assert_not_called()


@pytest.mark.asyncio
async def test_parashah(mocker):
    spy, spy_slack, tweet_id = await base_flow(mocker, "What's the parashah?", 1234, 4567)
    spy.assert_called_once_with(in_reply_to_tweet_id=tweet_id, text=f"The Parashah is {get_current_parashah(lang='eng')}")
    spy_slack.assert_not_called()


@pytest.mark.asyncio
async def test_parashah_heb(mocker):
    spy, spy_slack, tweet_id = await base_flow(mocker, "מה פרשת השבוע?", 1234, 4567)
    spy.assert_called_once_with(in_reply_to_tweet_id=tweet_id, text=f"פרשת השבוע היא פרשת {get_current_parashah(lang='heb')}")
    spy_slack.assert_not_called()


@pytest.mark.asyncio
async def test_unsupported_command(mocker):
    spy, spy_slack, tweet_id = await base_flow(mocker, "What's up dude?", 1234, 4567)
    spy.assert_not_called()
    spy_slack.assert_not_called()


@pytest.mark.asyncio
async def test_error_notifies_slack(mocker):
    spy, spy_slack, tweet_id = await base_flow(mocker, None, 1234, 4567)
    spy.assert_not_called()
    assert spy_slack.call_count == 1
    assert spy_slack.call_args[1]["channel"] == "#hebrew-year-process"
    assert "exception" in spy_slack.call_args[1]["text"]