import asyncio
import traceback

from tweepy import StreamRule

from src.config import get_mastodon_stream_listener, get_mastodon_client, get_slack_client
from src.utils import send_slack_alert


def reply():
    sc = get_slack_client()
    while True:
        try:
            mastodon_client = get_mastodon_client()
            stream = get_mastodon_stream_listener(mastodon_client=mastodon_client)
            mastodon_client.stream_user(stream)
        except Exception as e:
            send_slack_alert(sc, "exception: " + repr(e) + "\n" + traceback.format_exc())


if __name__ == '__main__':
    print("starting...")
    reply()
