import traceback

from mastodon import Mastodon, StreamListener

from hypb.tweet_helper import get_text_to_reply
from hypb.utils import send_alert


class _StreamingListener(StreamListener):
    """Extends AsyncStreamingClient to accept function, to be invoked for every new tweet"""

    def __init__(self, mastodon_client: Mastodon, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mastodon_client = mastodon_client

    def _dispatch(self, event):
        """Ignore empty events, so a server keepalive cannot kill the stream.

        mastodon-py 1.8.1 has a bug in its SSE parsing: `_parse_line()` handles a
        ':' comment line by calling `handle_heartbeat()` and returning the event
        dict untouched — still empty. The blank line that terminates the comment
        block then reaches `_dispatch({})`, which reads `event['event']` and
        raises MastodonMalformedEventError.

        Mastodon sends a keepalive roughly every 15 seconds, so without this
        guard the replier cannot stay connected for longer than that.

        Upstream fixed it the same way in 2.x, where `_dispatch` opens with
        `if not event: return`. Backporting it here keeps us on the pinned 1.8.1
        and makes this override a harmless no-op once that upgrade happens.
        """
        if not event:
            return None
        return super()._dispatch(event)

    def on_notification(self, notification):
        if notification["type"] == "mention":
            try:
                reply = get_text_to_reply(notification.status.content.lower())
                if reply:
                    return self.reply_to_toot(notification, reply)
            except Exception as e:
                send_alert("exception: " + repr(e) + "\n" + traceback.format_exc())

    def reply_to_toot(self, notification, message: str):
        return self.mastodon_client.status_reply(to_status=notification.status, status=message)
