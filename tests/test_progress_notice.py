"""The daily progress job's summary: today's bar, and what each platform did with it."""

from hypb.progress_notice import build_progress_summary


def test_the_summary_shows_the_bar_and_each_platform_outcome():
    message = build_progress_summary(8, "▓░░░░░░░░░░░░░░ 8%", {"mastodon": "posted", "twitter": "skipped"})

    assert message.html.splitlines() == [
        "📊 <b>Year progress · 8%</b>",
        "<code>▓░░░░░░░░░░░░░░ 8%</code>",
        "Mastodon ✅ posted · Twitter ⏸ skipped",
    ]


def test_every_outcome_has_its_mark():
    message = build_progress_summary(0, "bar", {"mastodon": "seeded", "twitter": "failed"})

    assert message.html.splitlines()[-1] == "Mastodon 🌱 seeded · Twitter ❌ failed"


def test_an_unknown_outcome_is_shown_rather_than_dropped():
    message = build_progress_summary(0, "bar", {"mastodon": "mystery"})

    assert message.html.splitlines()[-1] == "Mastodon • mystery"
