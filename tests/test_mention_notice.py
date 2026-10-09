"""The Telegram card sent for every mention the replier receives."""

from hypb.mention_notice import MAX_NOTICE_TEXT_CHARS, build_mention_notice
from hypb.mention_outcome import MentionOutcome
from hypb.telegram_message import MAX_MESSAGE_CHARS, LinkButton


def _notification(
    content="<p>מתי החג הבא?</p>",
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
    message = build_mention_notice(_notification(), MentionOutcome.replied("החג הקרוב הוא חנוכה"))

    assert message.html.splitlines() == [
        "✅ <b>Replied</b> · public",
        '👤 <a href="https://mastodon.social/@someone">@someone@mastodon.social</a>',
        "<blockquote>מתי החג הבא?</blockquote>",
        "↳ <i>החג הקרוב הוא חנוכה</i>",
    ]


def test_the_card_has_a_button_to_the_toot():
    message = build_mention_notice(_notification(), MentionOutcome.replied("x"))

    assert message.button == LinkButton("Open on Mastodon ↗", "https://mastodon.social/@someone/1")


def test_a_no_keyword_card():
    message = build_mention_notice(_notification(visibility="unlisted"), MentionOutcome.no_keyword())

    assert message.html.splitlines()[0] == "💤 <b>No keyword matched</b> · unlisted"
    assert "↳" not in message.html


def test_a_skipped_card_says_how_old_the_mention_was():
    message = build_mention_notice(_notification(), MentionOutcome.skipped(age_minutes=47))

    assert message.html.splitlines()[0] == "⏭ <b>Skipped</b> · 47 min old"


def test_a_failed_card_carries_the_error_and_a_collapsed_traceback():
    message = build_mention_notice(_notification(), MentionOutcome.failed(_raised(RuntimeError("boom"))))

    assert message.html.splitlines()[0] == "❌ <b>Reply failed</b> · public"
    assert "<code>RuntimeError(&#x27;boom&#x27;)</code>" in message.html
    assert "<blockquote expandable>Traceback (most recent call last):" in message.html
    assert len(message.plain()) <= MAX_MESSAGE_CHARS


def test_html_is_stripped_from_the_toot_and_what_remains_is_escaped():
    content = '<p><span class="h-card"><a href="https://x/@bot">@<span>bot</span></a></span> is 1 &lt; 2?</p>'

    message = build_mention_notice(_notification(content=content), MentionOutcome.no_keyword())

    assert "<blockquote>@bot is 1 &lt; 2?</blockquote>" in message.html


def test_a_hostile_username_and_answer_cannot_inject_markup():
    message = build_mention_notice(_notification(acct="<b>evil</b>"), MentionOutcome.replied("<a href='x'>y</a>"))

    assert "<b>evil</b>" not in message.html
    assert "<a href='x'>" not in message.html


def test_long_text_is_truncated():
    message = build_mention_notice(_notification(content="x" * (MAX_NOTICE_TEXT_CHARS + 50)), MentionOutcome.no_keyword())

    assert "x" * MAX_NOTICE_TEXT_CHARS in message.html
    assert "x" * (MAX_NOTICE_TEXT_CHARS + 1) not in message.html
    assert "50 more chars" in message.html


def test_missing_fields_do_not_raise():
    message = build_mention_notice({"type": "mention"}, MentionOutcome.no_keyword())

    assert message.html.splitlines()[0] == "💤 <b>No keyword matched</b>"
    assert "👤 unknown" in message.html
    assert message.button is None


def test_a_profile_or_toot_url_that_is_not_a_web_link_is_not_made_clickable():
    message = build_mention_notice(_notification(profile="javascript:x", url="javascript:y"), MentionOutcome.no_keyword())

    assert "href" not in message.html
    assert message.button is None
