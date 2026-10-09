"""The Telegram notice sent for every mention the replier receives.

The replier's logs say what it did, but nobody tails `docker logs` to learn that
someone asked it something. A message per mention puts the question, and what the
bot made of it, in front of the person who runs the bot.
"""

from html.parser import HTMLParser

#: Toot bodies are arbitrary user input; a long one would bury the rest of the notice.
MAX_NOTICE_TEXT_CHARS = 500

_UNKNOWN = "unknown"


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data):
        self._chunks.append(data)

    @property
    def text(self) -> str:
        return " ".join("".join(self._chunks).split())


def _strip_html(content: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(content)
    extractor.close()
    return extractor.text


def truncate(text: str) -> str:
    if len(text) <= MAX_NOTICE_TEXT_CHARS:
        return text
    return text[:MAX_NOTICE_TEXT_CHARS] + f"... [{len(text) - MAX_NOTICE_TEXT_CHARS} more chars]"


def build_mention_notice(notification, outcome: str) -> str:
    """Describe one mention and what the replier did about it.

    `outcome` is a short human-readable line supplied by the caller, because only
    the caller knows whether it replied, stayed silent or failed.
    """
    status = notification.get("status") or {}
    account = notification.get("account") or {}
    acct = account.get("acct")

    return "\n".join(
        [
            "mastodon mention",
            f"from: {'@' + acct if acct else _UNKNOWN}",
            f"text: {truncate(_strip_html(status.get('content') or ''))}",
            f"outcome: {outcome}",
            f"link: {status.get('url') or _UNKNOWN}",
        ]
    )
