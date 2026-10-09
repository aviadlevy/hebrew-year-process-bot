"""Each way a mention can end knows how it reads on the card."""

from hypb.mention_outcome import Failed, NoKeyword, Replied, Skipped

STATUS = {"visibility": "public"}


def _raised(error):
    try:
        raise error
    except Exception as e:
        return e


def test_replied_shows_the_answer_in_a_quote():
    outcome = Replied("החג הקרוב הוא חנוכה")

    assert (outcome.emoji, outcome.title, outcome.detail(STATUS)) == ("✅", "Replied", "public")
    assert outcome.lines() == ["<blockquote>🤖 החג הקרוב הוא חנוכה</blockquote>"]
    assert outcome.details() is None


def test_no_keyword_adds_nothing():
    outcome = NoKeyword()

    assert (outcome.emoji, outcome.title, outcome.detail(STATUS)) == ("💤", "No keyword matched", "public")
    assert outcome.lines() == []


def test_skipped_says_how_old_instead_of_the_visibility():
    outcome = Skipped(age_minutes=47)

    assert (outcome.emoji, outcome.title, outcome.detail(STATUS)) == ("⏭", "Skipped", "47 min old")


def test_failed_shows_the_error_and_carries_the_traceback():
    outcome = Failed(_raised(RuntimeError("boom")))

    assert (outcome.emoji, outcome.title) == ("❌", "Reply failed")
    assert outcome.lines() == ["<code>RuntimeError(&#x27;boom&#x27;)</code>"]
    assert outcome.details().endswith("RuntimeError: boom")


def test_a_status_without_visibility_has_no_detail():
    assert Replied("x").detail({}) is None
