"""The Telegram notice sent for every mention the replier receives."""

from hypb.mention_notice import MAX_NOTICE_TEXT_CHARS, build_mention_notice


def _notification(content="What's the date?", acct="someone@mastodon.social", url="https://mastodon.social/@someone/1"):
    return {"type": "mention", "account": {"acct": acct}, "status": {"content": content, "url": url}}


def test_notice_names_sender_text_outcome_and_link():
    notice = build_mention_notice(_notification(), outcome="replied")

    assert notice.splitlines() == [
        "mastodon mention",
        "from: @someone@mastodon.social",
        "text: What's the date?",
        "outcome: replied",
        "link: https://mastodon.social/@someone/1",
    ]


def test_html_is_stripped_from_the_toot_body():
    content = '<p><span class="h-card"><a href="https://x/@bot">@<span>bot</span></a></span> when is the next holiday?</p>'

    notice = build_mention_notice(_notification(content=content), outcome="replied")

    assert "text: @bot when is the next holiday?" in notice
    assert "<" not in notice


def test_hebrew_text_survives():
    notice = build_mention_notice(_notification(content="<p>מה התאריך?</p>"), outcome="replied")

    assert "text: מה התאריך?" in notice


def test_long_text_is_truncated():
    notice = build_mention_notice(_notification(content="x" * (MAX_NOTICE_TEXT_CHARS + 50)), outcome="replied")

    assert "x" * MAX_NOTICE_TEXT_CHARS in notice
    assert "x" * (MAX_NOTICE_TEXT_CHARS + 1) not in notice
    assert "50 more chars" in notice


def test_missing_fields_do_not_raise():
    notice = build_mention_notice({"type": "mention"}, outcome="not replied")

    assert "from: unknown" in notice
    assert "link: unknown" in notice
