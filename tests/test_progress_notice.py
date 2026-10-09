"""The daily progress job's summary: today's bar, and what each platform did with it."""

from hypb.post_outcome import PostOutcome
from hypb.progress_notice import build_progress_summary


def test_the_summary_shows_the_bar_once_and_each_platform_outcome():
    """The bar is plain text (monospace drew `░` as a solid block) and the % is in the title only."""
    message = build_progress_summary(8, "▓░░░░░░░░░░░░░░ 8%", {"mastodon": PostOutcome.POSTED, "twitter": PostOutcome.SKIPPED})

    assert message.html.splitlines() == [
        "📊 <b>Year progress · 8%</b>",
        "▓░░░░░░░░░░░░░░",
        "Mastodon ✅ posted · Twitter ⏸ skipped",
    ]


def test_every_outcome_has_its_mark():
    message = build_progress_summary(0, "░ 0%", {"mastodon": PostOutcome.SEEDED, "twitter": PostOutcome.FAILED})

    assert message.html.splitlines()[-1] == "Mastodon 🌱 seeded · Twitter ❌ failed"


def test_every_post_outcome_has_a_mark():
    message = build_progress_summary(0, "░ 0%", {str(o): o for o in PostOutcome})

    assert "•" not in message.html
