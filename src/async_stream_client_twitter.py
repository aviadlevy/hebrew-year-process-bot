import traceback

from tweepy import Tweet
from tweepy.asynchronous import AsyncClient, AsyncStreamingClient

from src.tweet_helper import get_text_to_reply
from src.utils import send_async_alert


class _AsyncStreamingClient(AsyncStreamingClient):
    """Extends AsyncStreamingClient to accept function, to be invoked for every new tweet"""

    def __init__(self, async_client: AsyncClient, user_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.async_client = async_client
        self.user_id = user_id

    async def on_tweet(self, tweet):
        try:
            if tweet.author_id == self.user_id:
                return
            reply = get_text_to_reply(tweet.text.lower())
            if reply:
                return await self.reply_to_tweet(tweet, reply)
        except Exception as e:
            await send_async_alert("exception: " + repr(e) + "\n" + traceback.format_exc())

    async def reply_to_tweet(self, tweet: Tweet, message: str):
        return await self.async_client.create_tweet(in_reply_to_tweet_id=tweet.id, text=message)
