"""Alerts: a title you can read at a glance, the error, and the traceback folded away."""

from hypb.alert_messages import MAX_ERROR_CHARS, error_alert, error_line, warning_alert
from hypb.telegram_message import MAX_MESSAGE_UNITS, visible_text
from hypb.text import utf16_len


def _raised(error):
    try:
        raise error
    except Exception as e:
        return e


def test_an_error_alert_has_a_title_the_error_and_a_collapsed_traceback():
    message = error_alert("Replier crashed", _raised(RuntimeError("boom")))

    assert message.html.startswith("🚨 <b>Replier crashed</b>\n<code>RuntimeError(&#x27;boom&#x27;)</code>")
    assert "<blockquote expandable>Traceback (most recent call last):" in message.html
    assert message.html.endswith("RuntimeError: boom</blockquote>")


def test_markup_in_a_traceback_is_escaped():
    """`File "<stdin>"` is what got the preview's crash alert rejected."""
    message = error_alert("Replier crashed", _raised(ValueError("<stdin> & <b>")))

    assert "<stdin>" not in message.html
    assert "&lt;stdin&gt; &amp; &lt;b&gt;" in message.html


def test_the_error_line_is_short_so_it_does_not_bury_the_alert():
    """A 6000-character error filled the screen in the preview; the traceback still has all of it."""
    line = error_line(_raised(RuntimeError("x" * 6000)))

    assert len(visible_text(line)) <= MAX_ERROR_CHARS + len("... [9999 more chars]")
    assert MAX_ERROR_CHARS == 150


def test_a_huge_error_still_fits_telegram_and_keeps_the_traceback_end():
    message = error_alert("Replier crashed", _raised(RuntimeError("😀" * 10_000)))

    assert utf16_len(visible_text(message.html)) <= MAX_MESSAGE_UNITS
    assert message.html.endswith("😀</blockquote>")


def test_an_error_that_was_never_raised_still_formats():
    """Some callers build the alert from an exception object, outside its except block."""
    message = error_alert("Poll failed", RuntimeError("no traceback"))

    assert "RuntimeError: no traceback" in message.html


def test_a_warning_has_a_title_and_a_detail():
    message = warning_alert("Mention polling failing for 5m · still retrying", "MastodonNetworkError('down')")

    assert message.html == "⚠️ <b>Mention polling failing for 5m · still retrying</b>\n<code>MastodonNetworkError(&#x27;down&#x27;)</code>"
