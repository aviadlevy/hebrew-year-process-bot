import asyncio

from tweepy import StreamRule

from config import get_async_stream

RULE_VALUE = "@yearprogressheb -is:retweet"
RULE_TAG = "mentions tweets"


async def reply():
    stream = get_async_stream()
    await stream.add_rules([StreamRule(value=RULE_VALUE, tag=RULE_TAG)])
    await stream.filter(expansions=["author_id"])


if __name__ == '__main__':
    print("starting...")
    exit(asyncio.run(reply()))
