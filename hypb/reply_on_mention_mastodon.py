import traceback

from hypb.config import get_mastodon_client, get_mastodon_stream_listener
from hypb.utils import send_alert


def reply():
    while True:
        try:
            mastodon_client = get_mastodon_client()
            stream = get_mastodon_stream_listener(mastodon_client=mastodon_client)
            mastodon_client.stream_user(stream)
        except Exception as e:
            send_alert("exception: " + repr(e) + "\n" + traceback.format_exc())


if __name__ == "__main__":
    print("starting...")
    reply()
