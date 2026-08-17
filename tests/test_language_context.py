"""Guards the two hazards in hdate 1.x's language handling.

1. hdate 1.x defaults to Hebrew; 0.11 defaulted to English. An English code
   path that relies on the default replies in Hebrew and nothing fails.
2. Language is a process-wide ContextVar, and mastodon-py dispatches
   on_notification on a background thread.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from pytz import timezone

from hypb.constant import TZ
from hypb.dates_helper import get_current_date

ORDINARY_DAY = timezone(TZ).localize(datetime(2026, 8, 17, 10, 0))


def test_english_is_actually_english():
    """hdate 1.x defaults to Hebrew, so the eng path must set language explicitly."""
    assert get_current_date(lang="eng", now_tz=ORDINARY_DAY) == "4 Elul 5786"


def test_hebrew_is_actually_hebrew():
    assert get_current_date(lang="heb", now_tz=ORDINARY_DAY) == "ד' אלול ה' תשפ\"ו"


def test_language_does_not_leak_between_threads():
    """Concurrent mentions in different languages must not contaminate each other."""
    expected = {"eng": "4 Elul 5786", "heb": "ד' אלול ה' תשפ\"ו"}
    langs = ["eng", "heb"] * 25

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda lang: (lang, get_current_date(lang=lang, now_tz=ORDINARY_DAY)), langs))

    for lang, got in results:
        assert got == expected[lang], f"{lang} returned {got!r}"


def test_language_is_restored_after_the_block():
    get_current_date(lang="heb", now_tz=ORDINARY_DAY)
    assert get_current_date(lang="eng", now_tz=ORDINARY_DAY) == "4 Elul 5786"
