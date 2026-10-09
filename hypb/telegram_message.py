"""The one shape every Telegram message takes, and the formatting it is built from.

Messages are sent as Telegram HTML so they can carry bold titles, quotes, a
collapsed traceback and a link button. That makes escaping a correctness rule,
not a nicety: anything from outside -- a toot, a username, a traceback -- that
contains a `<` would otherwise be read as a tag, and Telegram rejects the whole
message. Every helper below therefore escapes what it wraps, so a builder that
only composes helpers cannot forget.

Telegram also rejects a message longer than 4096 UTF-16 units. The message
enforces that itself rather than trusting every builder's arithmetic: the
collapsed details (a traceback) are the only part that can grow without bound,
so they are what gives way.
"""

import html
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from hypb.text import keep_end, utf16_len

#: Telegram's ceiling for a message's text after its markup is parsed, in UTF-16 units.
MAX_MESSAGE_UNITS = 4096

_TAG = re.compile(r"<[^>]+>")

#: Collapsed details are dropped rather than squeezed below this many UTF-16
#: units: a few lines of a traceback help nobody.
MIN_DETAILS_UNITS = 200


def escape(text: str) -> str:
    return html.escape(text, quote=True)


def bold(text: str) -> str:
    return f"<b>{escape(text)}</b>"


def italic(text: str) -> str:
    return f"<i>{escape(text)}</i>"


def code(text: str) -> str:
    return f"<code>{escape(text)}</code>"


def quote(text: str) -> str:
    return f"<blockquote>{escape(text)}</blockquote>"


def is_web_url(url: str | None) -> bool:
    """An http(s) URL with a real host -- the only kind Telegram takes on a button."""
    if not url or any(char.isspace() for char in url):
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def link(text: str, url: str | None) -> str:
    """A clickable link, or just the text when the URL is not a usable web link.

    URLs here come from Mastodon, which means from other people; only http(s)
    may become clickable.
    """
    if not is_web_url(url):
        return escape(text)
    return f'<a href="{escape(url)}">{escape(text)}</a>'


def visible_text(markup: str) -> str:
    """What a reader sees: the markup removed and escaped text restored.

    Safe to do with a regex only because every piece of outside text was
    escaped on the way in, so the only `<` left are our own tags.
    """
    return html.unescape(_TAG.sub("", markup))


@dataclass(frozen=True)
class LinkButton:
    text: str
    url: str


@dataclass(frozen=True)
class TelegramMessage:
    """A message as Telegram HTML, with collapsed details and a link button, both optional.

    `body` is HTML built from the helpers above. `details` is raw text -- a
    traceback -- shown in a collapsed quote and trimmed from its start until the
    whole message fits.
    """

    body: str
    details: str | None = None
    button: LinkButton | None = None

    @property
    def html(self) -> str:
        if not self.details:
            return self.body
        # One unit for the newline between the body and the collapsed quote.
        room = MAX_MESSAGE_UNITS - utf16_len(visible_text(self.body)) - 1
        if room < MIN_DETAILS_UNITS:
            return self.body
        return f"{self.body}\n<blockquote expandable>{escape(keep_end(self.details, room))}</blockquote>"

    def payload(self, chat_id: str) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": self.html,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }
        if self.button is not None:
            payload["reply_markup"] = {"inline_keyboard": [[{"text": self.button.text, "url": self.button.url}]]}
        return payload

    def plain_payload(self, chat_id: str) -> dict:
        """The fallback when Telegram rejects the formatted version.

        No markup, and no button: the button's URL may itself be what Telegram
        refused, so the link travels as text. Cut from the start, because the
        end of an alert is where its traceback names the failure.
        """
        lines = [visible_text(self.body)]
        if self.details:
            lines.append(self.details)
        if self.button is not None:
            lines.append(f"🔗 {self.button.url}")
        return {
            "chat_id": chat_id,
            "text": keep_end("\n".join(lines), MAX_MESSAGE_UNITS),
            "link_preview_options": {"is_disabled": True},
        }
