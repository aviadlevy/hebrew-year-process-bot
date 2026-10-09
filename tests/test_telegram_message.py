"""The one shape every Telegram message takes, and the formatting it is built from.

Every helper escapes what it is given, so text from outside -- a toot, a
username, a traceback -- can never be read as markup. A stray `<` in a traceback
was enough for Telegram to reject a whole alert in the preview.
"""

from hypb.telegram_message import (
    MAX_MESSAGE_UNITS,
    LinkButton,
    TelegramMessage,
    bold,
    code,
    is_web_url,
    italic,
    link,
    quote,
    visible_text,
)
from hypb.text import utf16_len


def test_helpers_escape_what_they_wrap():
    hostile = '<b>x</b> & "y"'

    for helper in (bold, italic, code, quote):
        rendered = helper(hostile)
        assert "<b>x</b>" not in rendered, helper.__name__
        assert "&lt;b&gt;x&lt;/b&gt; &amp;" in rendered, helper.__name__


def test_helpers_produce_telegram_html():
    assert bold("a") == "<b>a</b>"
    assert italic("a") == "<i>a</i>"
    assert code("a") == "<code>a</code>"
    assert quote("a") == "<blockquote>a</blockquote>"


def test_a_link_escapes_its_text_and_its_url():
    assert link("a<b", "https://x.example/?q=1&r=2") == '<a href="https://x.example/?q=1&amp;r=2">a&lt;b</a>'


def test_only_a_well_formed_web_url_counts_as_one():
    """A toot can carry any URL; Telegram rejects a button whose URL it cannot use."""
    assert is_web_url("https://mastodon.social/@a/1")
    assert is_web_url("http://example.org")
    for bad in (None, "", "javascript:alert(1)", "https://", "https://bad host/x", "ftp://x.example"):
        assert not is_web_url(bad), bad


def test_a_link_to_anything_but_a_web_url_is_plain_text():
    assert link("click", "javascript:alert(1)") == "click"
    assert link("click", None) == "click"


def test_visible_text_is_what_a_reader_sees():
    assert visible_text(f"{bold('Title')}\n{code('a < b & c')}") == "Title\na < b & c"


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


def test_details_are_collapsed_and_escaped():
    message = TelegramMessage("🚨 <b>Crashed</b>", details='File "<stdin>", line 1')

    assert message.html == "🚨 <b>Crashed</b>\n<blockquote expandable>File &quot;&lt;stdin&gt;&quot;, line 1</blockquote>"


def test_details_give_way_so_the_whole_message_fits_telegram():
    """The traceback is the only part that can grow without bound, so it is what shrinks."""
    body = bold("Crashed") + "\n" + quote("😀" * 500)
    message = TelegramMessage(body, details="frame\n" * 2000 + "RuntimeError: the end")

    assert utf16_len(visible_text(message.html)) <= MAX_MESSAGE_UNITS
    assert message.html.endswith("RuntimeError: the end</blockquote>")
    assert "earlier characters trimmed" in message.html


def test_short_details_are_untouched():
    assert TelegramMessage("t", details="short").html == "t\n<blockquote expandable>short</blockquote>"


def test_the_plain_fallback_has_no_markup_no_button_and_the_link_as_text():
    """The button itself may be why Telegram refused the message; the retry must not carry it."""
    message = TelegramMessage(bold("Replied"), button=LinkButton("Open on Mastodon ↗", "https://mastodon.social/@a/1"))

    payload = message.plain_payload("42")

    assert "parse_mode" not in payload
    assert "reply_markup" not in payload
    assert payload["text"] == "Replied\n🔗 https://mastodon.social/@a/1"


def test_the_plain_fallback_keeps_the_end_and_fits_in_utf16_units():
    message = TelegramMessage(code("😀" * 3000), details="x" * 5000 + " the end")

    text = message.plain_payload("42")["text"]

    assert utf16_len(text) <= MAX_MESSAGE_UNITS
    assert text.endswith("the end")


def test_details_are_dropped_when_the_body_alone_fills_the_message():
    """The body is never cut (it is HTML); the plain fallback is what saves a body this long."""
    body = code("x" * MAX_MESSAGE_UNITS)

    assert TelegramMessage(body, details="traceback").html == body
