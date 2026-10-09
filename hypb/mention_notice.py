"""The Telegram card sent for every mention the replier receives.

The replier's logs say what it did, but nobody tails `docker logs` to learn that
someone asked it something. A card per mention puts the question, and what the
bot made of it, in front of the person who runs the bot.
"""

from html.parser import HTMLParser

from hypb.alert_messages import MAX_TRACEBACK_CHARS, format_traceback
from hypb.mention_outcome import MentionOutcome, OutcomeKind
from hypb.telegram_message import (
    LinkButton,
    TelegramMessage,
    bold,
    code,
    escape,
    expandable_quote,
    is_web_url,
    italic,
    link,
    quote,
)
from hypb.text import keep_end, truncate

#: Toot bodies are arbitrary user input; a long one would bury the rest of the card.
MAX_NOTICE_TEXT_CHARS = 500

_UNKNOWN = "unknown"

#: The emoji and title that open each card, by outcome.
_HEADERS = {
    OutcomeKind.REPLIED: ("✅", "Replied"),
    OutcomeKind.NO_KEYWORD: ("💤", "No keyword matched"),
    OutcomeKind.SKIPPED: ("⏭", "Skipped"),
    OutcomeKind.FAILED: ("❌", "Reply failed"),
}


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


def _header(status, outcome: MentionOutcome) -> str:
    emoji, title = _HEADERS[outcome.kind]
    detail = f"{outcome.age_minutes} min old" if outcome.kind is OutcomeKind.SKIPPED else status.get("visibility")
    header = f"{emoji} {bold(title)}"
    return f"{header} · {escape(detail)}" if detail else header


def _sender(account) -> str:
    acct = account.get("acct")
    if not acct:
        return f"👤 {_UNKNOWN}"
    return f"👤 {link('@' + acct, account.get('url'))}"


def _outcome_lines(outcome: MentionOutcome) -> list[str]:
    if outcome.kind is OutcomeKind.REPLIED:
        return [f"↳ {italic(outcome.reply_text or '')}"]
    if outcome.kind is OutcomeKind.FAILED and outcome.error is not None:
        return [code(repr(outcome.error)), expandable_quote(keep_end(format_traceback(outcome.error), MAX_TRACEBACK_CHARS))]
    return []


def build_mention_notice(notification, outcome: MentionOutcome) -> TelegramMessage:
    """One card per mention: outcome, sender, the question, then what the bot did."""
    status = notification.get("status") or {}
    account = notification.get("account") or {}
    question = truncate(_strip_html(status.get("content") or ""), MAX_NOTICE_TEXT_CHARS)

    lines = [_header(status, outcome), _sender(account), quote(question), *_outcome_lines(outcome)]
    url = status.get("url")
    button = LinkButton("Open on Mastodon ↗", url) if is_web_url(url) else None
    return TelegramMessage("\n".join(lines), button=button)
