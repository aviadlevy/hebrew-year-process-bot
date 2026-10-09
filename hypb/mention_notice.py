"""The Telegram card sent for every mention the replier receives.

The replier's logs say what it did, but nobody tails `docker logs` to learn that
someone asked it something. A card per mention puts the question, and what the
bot made of it, in front of the person who runs the bot.
"""

import re
from html.parser import HTMLParser

from hypb.mention_outcome import MentionOutcome
from hypb.telegram_message import (
    LinkButton,
    TelegramMessage,
    bold,
    escape,
    is_web_url,
    link,
    quote,
)
from hypb.text import truncate

#: Toot bodies are arbitrary user input; a long one would bury the rest of the card.
MAX_NOTICE_TEXT_CHARS = 500

#: Account names come from remote servers; keep the sender line to one line.
MAX_ACCT_CHARS = 100

_UNKNOWN = "unknown"

#: The handles a toot opens with -- always the bot's own, sometimes a thread's.
_LEADING_MENTIONS = re.compile(r"^(?:@\S+\s+)+")


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


def _question(content: str) -> str:
    """The toot's text without the handles it opens with, unless that is all it has."""
    text = _strip_html(content)
    return _LEADING_MENTIONS.sub("", text) or text


def _header(status, outcome: MentionOutcome) -> str:
    header = f"{outcome.emoji} {bold(outcome.title)}"
    detail = outcome.detail(status)
    return f"{header} · {escape(detail)}" if detail else header


def _sender(account) -> str:
    acct = account.get("acct")
    if not acct:
        return f"👤 {_UNKNOWN}"
    return f"👤 {link('@' + truncate(acct, MAX_ACCT_CHARS), account.get('url'))}"


def build_mention_notice(notification, outcome: MentionOutcome) -> TelegramMessage:
    """One card per mention: outcome, sender, the question, then what the bot did."""
    status = notification.get("status") or {}
    account = notification.get("account") or {}
    question = truncate(_question(status.get("content") or ""), MAX_NOTICE_TEXT_CHARS)

    lines = [_header(status, outcome), _sender(account), quote(question), *outcome.lines()]
    url = status.get("url")
    button = LinkButton("Open on Mastodon ↗", url) if is_web_url(url) else None
    return TelegramMessage("\n".join(lines), details=outcome.details(), button=button)
