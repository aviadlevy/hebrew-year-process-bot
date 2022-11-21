import traceback

import slack
from mastodon import StreamListener, Mastodon

from tweet_helper import get_text_to_reply
from utils import send_slack_alert


class _StreamingListener(StreamListener):
    """Extends AsyncStreamingClient to accept function, to be invoked for every new tweet"""

    def __init__(self, mastodon_client: Mastodon, slack_client: slack.WebClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mastodon_client = mastodon_client
        self.sc = slack_client

    def on_notification(self, notification):
        if notification['type'] == 'mention':
            try:
                reply = get_text_to_reply(notification.status.content.lower())
                if reply:
                    return self.reply_to_toot(notification, reply)
            except Exception as e:
                send_slack_alert(self.sc, "exception: " + repr(e) + "\n" + traceback.format_exc())

    def reply_to_toot(self, notification, message: str):
        return self.mastodon_client.status_reply(to_status=notification.status, status=message)
