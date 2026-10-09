"""The one shape every Telegram message takes, and the formatting it is built from.

Every helper escapes what it is given, so text from outside -- a toot, a
username, a traceback -- can never be read as markup. A stray `<` in a traceback
was enough for Telegram to reject a whole alert in the preview.
"""

from hypb.telegram_message import (
    MAX_MESSAGE_CHARS,
    LinkButton,
    TelegramMessage,
    bold,
    code,
    expandable_quote,
    italic,
    link,
    quote,
)


def test_helpers_escape_what_they_wrap():
    hostile = '<b>x</b> & "y"'

    for helper in (bold, italic, code, quote, expandable_quote):
        rendered = helper(hostile)
        assert "<b>x</b>" not in rendered, helper.__name__
        assert "&lt;b&gt;x&lt;/b&gt; &amp;" in rendered, helper.__name__


def test_helpers_produce_telegram_html():
    assert bold("a") == "<b>a</b>"
    assert italic("a") == "<i>a</i>"
    assert code("a") == "<code>a</code>"
    assert quote("a") == "<blockquote>a</blockquote>"
    assert expandable_quote("a") == "<blockquote expandable>a</blockquote>"


def test_a_link_escapes_its_text_and_its_url():
    assert link("a<b", "https://x.example/?q=1&r=2") == '<a href="https://x.example/?q=1&amp;r=2">a&lt;b</a>'


def test_a_link_to_anything_but_http_is_plain_text():
    """A toot can carry any URL; only web links may become clickable."""
    assert link("click", "javascript:alert(1)") == "click"
    assert link("click", None) == "click"


def test_the_payload_asks_for_html_without_link_previews():
    payload = TelegramMessage("<b>hi</b>").payload("42")

    assert payload == {
        "chat_id": "42",
        "text": "<b>hi</b>",
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
    }


def test_a_button_becomes_an_inline_keyboard():
    message = TelegramMessage("hi", button=LinkButton("Open on Mastodon ↗", "https://mastodon.social/@a/1"))

    assert message.payload("42")["reply_markup"] == {
        "inline_keyboard": [[{"text": "Open on Mastodon ↗", "url": "https://mastodon.social/@a/1"}]]
    }


def test_plain_text_drops_the_markup_and_restores_escaped_text():
    message = TelegramMessage(f"{bold('Title')}\n{code('a < b & c')}")

    assert message.plain() == "Title\na < b & c"


def test_the_plain_payload_is_unformatted_and_fits_the_limit():
    """The fallback for a rejected message must not be rejected for the same reasons."""
    message = TelegramMessage(code("x" * (MAX_MESSAGE_CHARS + 100)), button=LinkButton("Open", "https://e.example"))

    payload = message.plain_payload("42")

    assert "parse_mode" not in payload
    assert len(payload["text"]) == MAX_MESSAGE_CHARS
    assert payload["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://e.example"
