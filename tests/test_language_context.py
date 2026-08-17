"""Guards the two hazards in hdate 1.x's language handling.

1. hdate 1.x defaults to Hebrew; 0.11 defaulted to English. An English code
   path that relies on the default replies in Hebrew and nothing fails.
2. Language is a ContextVar, not a per-object flag. Without resetting it,
   a Hebrew render leaks into any later hdate call in the same context that
   isn't itself wrapped in language() -- including a subsequent English
   render, or a render reached after an earlier call raised partway through.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from hdate.translator import context_language
from pytz import timezone

from hypb.constant import TZ
from hypb.dates_helper import get_current_date, get_hdate_from_pydate, language

ORDINARY_DAY = timezone(TZ).localize(datetime(2026, 8, 17, 10, 0))


def test_english_is_actually_english():
    """hdate 1.x defaults to Hebrew, so the eng path must set language explicitly."""
    assert get_current_date(lang="eng", now_tz=ORDINARY_DAY) == "4 Elul 5786"


def test_hebrew_is_actually_hebrew():
    assert get_current_date(lang="heb", now_tz=ORDINARY_DAY) == "ד' אלול ה' תשפ\"ו"


def test_language_is_restored_to_the_previous_value():
    token = context_language.set("en")
    try:
        with language("heb"):
            assert context_language.get() == "he"
        assert context_language.get() == "en"
    finally:
        context_language.reset(token)


def test_language_is_restored_when_the_block_raises():
    token = context_language.set("he")
    try:
        with pytest.raises(RuntimeError), language("eng"):
            raise RuntimeError
        assert context_language.get() == "he"
    finally:
        context_language.reset(token)


def test_concurrent_languages_are_live_at_the_same_time():
    barrier = threading.Barrier(2)

    def render(lang):
        with language(lang):
            barrier.wait(timeout=5)
            return str(get_hdate_from_pydate(now_tz=ORDINARY_DAY).hdate)

    with ThreadPoolExecutor(max_workers=2) as pool:
        got = list(pool.map(render, ["eng", "heb"]))

    assert got == ["4 Elul 5786", "ד' אלול ה' תשפ\"ו"]
