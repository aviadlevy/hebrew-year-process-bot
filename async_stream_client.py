from tweepy import Tweet
from tweepy.asynchronous import AsyncStreamingClient, AsyncClient

from dates_helper import get_current_date


class _AsyncStreamingClient(AsyncStreamingClient):
    """Extends AsyncStreamingClient to accept function, to be invoked for every new tweet"""

    def __init__(self, async_client: AsyncClient, user_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.async_client = async_client
        self.user_id = user_id

    async def on_tweet(self, tweet):
        if tweet.author_id == self.user_id:
            return
        if "date" in tweet.text.lower():
            return await self.reply_to_tweet(tweet, f"The date is:\n{get_current_date(lang='eng')}")
        elif "תאריך" in tweet.text.lower():
            return await self.reply_to_tweet(tweet, f"התאריך הוא:\n{get_current_date(lang='heb')}")

    async def reply_to_tweet(self, tweet: Tweet, message: str):
        return await self.async_client.create_tweet(in_reply_to_tweet_id=tweet.id, text=message)
