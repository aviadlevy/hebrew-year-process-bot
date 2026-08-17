# Dormant: Twitter's free tier no longer offers the filtered-stream access this
# module depends on (see the design doc's Non-goals). Left as-is rather than
# migrated to the newer conventions used elsewhere in this repo (logging,
# hypb.settings.require, an int-returning main()) since there is no live path
# to exercise it against.
import asyncio
import sys

from tweepy import StreamRule

from hypb.config import get_async_twitter_stream

RULE_VALUE = "@yearprogressheb -is:retweet"
RULE_TAG = "mentions tweets"


async def reply():
    stream = get_async_twitter_stream()
    await stream.add_rules([StreamRule(value=RULE_VALUE, tag=RULE_TAG)])
    await stream.filter(expansions=["author_id"])


if __name__ == "__main__":
    print("starting...")
    sys.exit(asyncio.run(reply()))
