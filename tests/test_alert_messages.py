"""Alerts: a title you can read at a glance, the error, and the traceback folded away."""

from hypb.alert_messages import MAX_TRACEBACK_CHARS, error_alert, warning_alert
from hypb.telegram_message import MAX_MESSAGE_CHARS


def _raised(error):
    try:
        raise error
    except Exception as e:
        return e


def test_an_error_alert_has_a_title_the_error_and_a_collapsed_traceback():
    message = error_alert("Replier crashed", _raised(RuntimeError("boom")))

    assert message.html.startswith("🚨 <b>Replier crashed</b>")
    assert "<code>RuntimeError(&#x27;boom&#x27;)</code>" in message.html
    assert "<blockquote expandable>Traceback (most recent call last):" in message.html
    assert "RuntimeError: boom" in message.html


def test_markup_in_a_traceback_is_escaped():
    """`File "<stdin>"` is what got the preview's crash alert rejected."""
    message = error_alert("Replier crashed", _raised(ValueError("<stdin> & <b>")))

    assert "<stdin>" not in message.html
    assert "&lt;stdin&gt; &amp; &lt;b&gt;" in message.html


def test_a_long_traceback_keeps_its_end_and_the_alert_fits_telegram():
    """The end of a traceback names the failure; the start is the least useful part to keep."""
    message = error_alert("Replier crashed", _raised(RuntimeError("x" * 10_000)))

    assert len(message.plain()) <= MAX_MESSAGE_CHARS
    assert "earlier characters trimmed" in message.html
    assert message.html.rstrip().endswith("x</blockquote>")


def test_the_error_line_is_capped_too():
    message = error_alert("Replier crashed", _raised(RuntimeError("y" * 10_000)))

    assert len(message.plain()) <= MAX_MESSAGE_CHARS
    assert MAX_TRACEBACK_CHARS < MAX_MESSAGE_CHARS


def test_an_error_that_was_never_raised_still_formats():
    """Some callers build the alert from an exception object, outside its except block."""
    message = error_alert("Poll failed", RuntimeError("no traceback"))

    assert "RuntimeError: no traceback" in message.html


def test_a_warning_has_a_title_and_a_detail():
    message = warning_alert("Mention polling failing for 5m · still retrying", "MastodonNetworkError('down')")

    assert message.html == "⚠️ <b>Mention polling failing for 5m · still retrying</b>\n<code>MastodonNetworkError(&#x27;down&#x27;)</code>"
