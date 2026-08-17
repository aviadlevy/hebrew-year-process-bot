"""Locks the bot's user-visible output across the hdate 0.11 -> 1.2 upgrade.

Every expected value here was produced by running the real dates_helper logic
under BOTH hdate 0.11.1 and 1.2.1; all of them are identical across the two.
If a test in this file fails after the upgrade, the migration changed what the
bot says to users. Fix the migration, never the assertion.
"""

from datetime import datetime

import pytest
from pytz import timezone

from hypb.constant import TZ
from hypb.dates_helper import (
    get_current_date,
    get_current_parashah,
    get_upcoming_holiday,
)


def holiday_name(holiday):
    """Return the holiday's display name under either hdate major version."""
    return holiday if isinstance(holiday, str) else holiday.holiday_description


def at(year, month, day, hour, minute):
    return timezone(TZ).localize(datetime(year, month, day, hour, minute))


ORDINARY_DAY = at(2026, 8, 17, 10, 0)
AFTER_TZET = at(2026, 8, 17, 21, 30)
EREV_YOM_TOV = at(2026, 9, 11, 10, 0)
YOM_TOV = at(2026, 9, 12, 10, 0)
MELACHA_PERMITTED = at(2026, 12, 6, 10, 0)
LEAP_ADAR_I = at(2027, 2, 15, 10, 0)
LEAP_ADAR_II = at(2027, 3, 15, 10, 0)

HEBREW_DATES = [
    (ORDINARY_DAY, "eng", "4 Elul 5786"),
    (ORDINARY_DAY, "heb", "ד' אלול ה' תשפ\"ו"),
    (AFTER_TZET, "eng", "5 Elul 5786"),
    (AFTER_TZET, "heb", "ה' אלול ה' תשפ\"ו"),
    (EREV_YOM_TOV, "eng", "29 Elul 5786"),
    (EREV_YOM_TOV, "heb", "כ\"ט אלול ה' תשפ\"ו"),
    (YOM_TOV, "eng", "1 Tishrei 5787"),
    (YOM_TOV, "heb", "א' תשרי ה' תשפ\"ז"),
    (MELACHA_PERMITTED, "eng", "26 Kislev 5787"),
    (MELACHA_PERMITTED, "heb", "כ\"ו כסלו ה' תשפ\"ז"),
    (LEAP_ADAR_I, "eng", "8 Adar I 5787"),
    (LEAP_ADAR_I, "heb", "ח' אדר א ה' תשפ\"ז"),
    (LEAP_ADAR_II, "eng", "6 Adar II 5787"),
    (LEAP_ADAR_II, "heb", "ו' אדר ב ה' תשפ\"ז"),
]


@pytest.mark.parametrize("now_tz, lang, expected", HEBREW_DATES)
def test_hebrew_date_is_stable(now_tz, lang, expected):
    assert get_current_date(lang=lang, now_tz=now_tz) == expected


PARASHOT = [
    (ORDINARY_DAY, "eng", "Ki Teitzei"),
    (ORDINARY_DAY, "heb", "כי תצא"),
    (EREV_YOM_TOV, "eng", "none"),
    (YOM_TOV, "eng", "none"),
    (MELACHA_PERMITTED, "eng", "Miketz"),
    (MELACHA_PERMITTED, "heb", "מקץ"),
    (LEAP_ADAR_I, "eng", "Tetzaveh"),
    (LEAP_ADAR_I, "heb", "תצוה"),
    (LEAP_ADAR_II, "eng", "Vayikra"),
    (LEAP_ADAR_II, "heb", "ויקרא"),
]


@pytest.mark.parametrize("now_tz, lang, expected", PARASHOT)
def test_parashah_is_stable(now_tz, lang, expected):
    assert get_current_parashah(lang=lang, now_tz=now_tz) == expected


HOLIDAYS = [
    (ORDINARY_DAY, "eng", "Rosh Hashana I", 26),
    (ORDINARY_DAY, "heb", "א' ראש השנה", 26),
    (AFTER_TZET, "eng", "Rosh Hashana I", 25),
    (EREV_YOM_TOV, "eng", "Rosh Hashana I", 1),
    (YOM_TOV, "eng", "Rosh Hashana I", 0),
    (MELACHA_PERMITTED, "eng", "Chanukah", 0),
    (MELACHA_PERMITTED, "heb", "חנוכה", 0),
    (LEAP_ADAR_I, "eng", "Purim", 36),
    (LEAP_ADAR_II, "eng", "Purim", 8),
    (LEAP_ADAR_II, "heb", "פורים", 8),
]


@pytest.mark.parametrize("now_tz, lang, expected_name, expected_delta", HOLIDAYS)
def test_upcoming_holiday_is_stable(now_tz, lang, expected_name, expected_delta):
    holiday, days_delta = get_upcoming_holiday(lang=lang, now_tz=now_tz)
    assert holiday_name(holiday) == expected_name
    assert days_delta == expected_delta
