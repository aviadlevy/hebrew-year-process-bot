"""The one shape every Telegram message takes, and the formatting it is built from.

Messages are sent as Telegram HTML so they can carry bold titles, quotes, a
collapsed traceback and a link button. That makes escaping a correctness rule,
not a nicety: anything from outside -- a toot, a username, a traceback -- that
contains a `<` would otherwise be read as a tag, and Telegram rejects the whole
message. Every helper below therefore escapes what it wraps, so a builder that
only composes helpers cannot forget.
"""

import html
import re
from dataclasses import dataclass

#: Telegram's ceiling for a message's text. Longer messages are rejected outright.
MAX_MESSAGE_CHARS = 4096

_TAG = re.compile(r"<[^>]+>")


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


def expandable_quote(text: str) -> str:
    """A quote Telegram shows collapsed until tapped; for tracebacks."""
    return f"<blockquote expandable>{escape(text)}</blockquote>"


def is_web_url(url: str | None) -> bool:
    return bool(url) and url.startswith(("https://", "http://"))


def link(text: str, url: str | None) -> str:
    """A clickable link, or just the text when the URL is not a web link.

    URLs here come from Mastodon, which means from other people; only http(s)
    may become clickable.
    """
    if not is_web_url(url):
        return escape(text)
    return f'<a href="{escape(url)}">{escape(text)}</a>'


@dataclass(frozen=True)
class LinkButton:
    text: str
    url: str


@dataclass(frozen=True)
class TelegramMessage:
    """A message as Telegram HTML, with an optional link button under it."""

    html: str
    button: LinkButton | None = None

    def payload(self, chat_id: str) -> dict:
        return self._with_button({
            "chat_id": chat_id,
            "text": self.html,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        })

    def plain(self) -> str:
        """The text with the markup removed, as a reader would see it.

        Safe to do with a regex only because every piece of outside text was
        escaped on the way in, so the only `<` left are our own tags.
        """
        return html.unescape(_TAG.sub("", self.html))

    def plain_payload(self, chat_id: str) -> dict:
        """The fallback when Telegram rejects the formatted version: no markup, within the limit."""
        return self._with_button({
            "chat_id": chat_id,
            "text": self.plain()[:MAX_MESSAGE_CHARS],
            "link_preview_options": {"is_disabled": True},
        })

    def _with_button(self, payload: dict) -> dict:
        if self.button is not None:
            payload["reply_markup"] = {"inline_keyboard": [[{"text": self.button.text, "url": self.button.url}]]}
        return payload
