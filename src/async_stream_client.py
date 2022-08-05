import traceback

import slack
from tweepy import Tweet
from tweepy.asynchronous import AsyncStreamingClient, AsyncClient

from src.lang import MESSAGES
from utils import send_slack_alert


class _AsyncStreamingClient(AsyncStreamingClient):
    """Extends AsyncStreamingClient to accept function, to be invoked for every new tweet"""

    def __init__(self, async_client: AsyncClient, slack_client: slack.AsyncWebClient, user_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.async_client = async_client
        self.sc = slack_client
        self.user_id = user_id

    async def on_tweet(self, tweet):
        try:
            if tweet.author_id == self.user_id:
                return
            if "date" in tweet.text.lower():
                return await self.reply_to_tweet(tweet, MESSAGES["date"]["eng"]())
            elif "תאריך" in tweet.text.lower():
                return await self.reply_to_tweet(tweet, MESSAGES["date"]["heb"]())
            elif "parasha" in tweet.text.lower():
                return await self.reply_to_tweet(tweet, MESSAGES["parashah"]["eng"]())
            elif any(x in tweet.text.lower() for x in ["פרשה", "פרשת"]):
                return await self.reply_to_tweet(tweet, MESSAGES["parashah"]["heb"]())
        except Exception as e:
            await send_slack_alert(self.sc, "exception: " + repr(e) + "\n" + traceback.format_exc())

    async def reply_to_tweet(self, tweet: Tweet, message: str):
        return await self.async_client.create_tweet(in_reply_to_tweet_id=tweet.id, text=message)
