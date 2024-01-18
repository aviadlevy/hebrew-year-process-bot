from datetime import datetime

import pytest
from pyluach.dates import HebrewDate
from pytz import timezone

from src.constant import TZ
from src.dates_helper import get_heb_date_from_pydate

get_heb_date_from_pydate_date = [
    (timezone(TZ).localize(datetime(2022, 8, 3, 18, 45)), HebrewDate(5782, 5, 6)),  # before subset
    (timezone(TZ).localize(datetime(2022, 8, 3, 20, 45)), HebrewDate(5782, 5, 7)),  # after sunset
    (timezone(TZ).localize(datetime(2022, 8, 4, 00, 45)), HebrewDate(5782, 5, 7))   # after midnight
]


@pytest.mark.parametrize("d, expected", get_heb_date_from_pydate_date)
def test_get_heb_date_from_pydate(d: datetime, expected: HebrewDate):
    assert get_heb_date_from_pydate(d) == expected
