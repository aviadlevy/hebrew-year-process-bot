"""The Telegram card sent for every mention the replier receives."""

from hypb.mention_notice import MAX_NOTICE_TEXT_CHARS, build_mention_notice
from hypb.mention_outcome import Failed, NoKeyword, Replied, Skipped
from hypb.telegram_message import MAX_MESSAGE_UNITS, LinkButton, visible_text
from hypb.text import utf16_len

BOT_MENTION = '<span class="h-card"><a href="https://mastodon.social/@yearProgressHeb">@<span>yearProgressHeb</span></a></span>'


def _notification(
    content=f"<p>{BOT_MENTION} <br>מתי החג הבא?</p>",
    acct="someone@mastodon.social",
    profile="https://mastodon.social/@someone",
    url="https://mastodon.social/@someone/1",
    visibility="public",
):
    return {
        "type": "mention",
        "account": {"acct": acct, "url": profile},
        "status": {"content": content, "url": url, "visibility": visibility},
    }


def _raised(error):
    try:
        raise error
    except Exception as e:
        return e


def test_a_replied_card_shows_who_asked_what_and_the_answer():
    message = build_mention_notice(_notification(), Replied("החג הקרוב הוא חנוכה"))

    assert message.html.splitlines() == [
        "✅ <b>Replied</b> · public",
        '👤 <a href="https://mastodon.social/@someone">@someone@mastodon.social</a>',
        "<blockquote>מתי החג הבא?</blockquote>",
        "<blockquote>🤖 החג הקרוב הוא חנוכה</blockquote>",
    ]


def test_the_card_has_a_button_to_the_toot():
    message = build_mention_notice(_notification(), Replied("x"))

    assert message.button == LinkButton("Open on Mastodon ↗", "https://mastodon.social/@someone/1")


def test_the_leading_mentions_are_dropped_from_the_question():
    """Every question starts with the bot's own handle; it says nothing."""
    content = f'<p><span class="h-card">@<span>aviadlevy</span></span> {BOT_MENTION} what is the date?</p>'

    message = build_mention_notice(_notification(content=content), NoKeyword())

    assert "<blockquote>what is the date?</blockquote>" in message.html


def test_a_mention_with_nothing_but_handles_keeps_them():
    message = build_mention_notice(_notification(content=f"<p>{BOT_MENTION}</p>"), NoKeyword())

    assert "<blockquote>@yearProgressHeb</blockquote>" in message.html


def test_a_no_keyword_card():
    message = build_mention_notice(_notification(visibility="unlisted"), NoKeyword())

    assert message.html.splitlines()[0] == "💤 <b>No keyword matched</b> · unlisted"
    assert len(message.html.splitlines()) == 3


def test_a_skipped_card_says_how_old_the_mention_was():
    message = build_mention_notice(_notification(), Skipped(age_minutes=47))

    assert message.html.splitlines()[0] == "⏭ <b>Skipped</b> · 47 min old"


def test_a_failed_card_carries_the_error_and_a_collapsed_traceback():
    message = build_mention_notice(_notification(), Failed(_raised(RuntimeError("boom"))))

    assert message.html.splitlines()[0] == "❌ <b>Reply failed</b> · public"
    assert "<code>RuntimeError(&#x27;boom&#x27;)</code>" in message.html
    assert "<blockquote expandable>Traceback (most recent call last):" in message.html


def test_the_worst_case_failed_card_still_fits_telegram():
    """A huge error and an emoji-heavy toot measured 9,108 UTF-16 units in review."""
    message = build_mention_notice(_notification(content="😀" * 5000), Failed(_raised(RuntimeError("e" * 5000))))

    assert utf16_len(visible_text(message.html)) <= MAX_MESSAGE_UNITS


def test_html_is_stripped_from_the_toot_and_what_remains_is_escaped():
    content = '<p><span class="h-card"><a href="https://x/@bot">@<span>bot</span></a></span> is 1 &lt; 2?</p>'

    message = build_mention_notice(_notification(content=content), NoKeyword())

    assert "<blockquote>is 1 &lt; 2?</blockquote>" in message.html


def test_a_hostile_username_and_answer_cannot_inject_markup():
    message = build_mention_notice(_notification(acct="<b>evil</b>"), Replied("<a href='x'>y</a>"))

    assert "<b>evil</b>" not in message.html
    assert "<a href='x'>" not in message.html


def test_long_text_is_truncated():
    message = build_mention_notice(_notification(content="x" * (MAX_NOTICE_TEXT_CHARS + 50)), NoKeyword())

    assert "x" * MAX_NOTICE_TEXT_CHARS in message.html
    assert "x" * (MAX_NOTICE_TEXT_CHARS + 1) not in message.html
    assert "50 more chars" in message.html


def test_missing_fields_do_not_raise():
    message = build_mention_notice({"type": "mention"}, NoKeyword())

    assert message.html.splitlines()[0] == "💤 <b>No keyword matched</b>"
    assert "👤 unknown" in message.html
    assert message.button is None


def test_a_profile_or_toot_url_that_is_not_a_web_link_is_not_made_clickable():
    message = build_mention_notice(_notification(profile="javascript:x", url="https://bad host/y"), NoKeyword())

    assert "href" not in message.html
    assert message.button is None


def test_a_handle_followed_by_a_line_break_is_still_dropped():
    """No space before the <br>: the text must not glue into '@yearProgressHebwhat'."""
    message = build_mention_notice(_notification(content=f"<p>{BOT_MENTION}<br />what is the date?</p>"), NoKeyword())

    assert "<blockquote>what is the date?</blockquote>" in message.html


def test_paragraphs_do_not_glue_together():
    message = build_mention_notice(_notification(content="<p>hi</p><p>second</p>"), NoKeyword())

    assert "<blockquote>hi second</blockquote>" in message.html


def test_a_mention_with_no_text_says_so_instead_of_an_empty_quote():
    message = build_mention_notice(_notification(content=""), NoKeyword())

    assert "<blockquote></blockquote>" not in message.html
    assert "<i>(no text)</i>" in message.html
