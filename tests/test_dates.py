from datetime import datetime

import hdate
import pytest
from hdate.htables import Months
from pytz import timezone

from hypb.constant import TZ
from hypb.dates_helper import get_hdate_from_pydate

get_heb_date_from_pydate_date = [
    (timezone(TZ).localize(datetime(2022, 8, 3, 18, 45)), hdate.HDate(heb_date=hdate.HebrewDate(5782, Months.AV, 6), hebrew=False)),  # before subset
    (timezone(TZ).localize(datetime(2022, 8, 3, 20, 45)), hdate.HDate(heb_date=hdate.HebrewDate(5782, Months.AV, 7), hebrew=False)),  # after sunset
    (timezone(TZ).localize(datetime(2022, 8, 4, 00, 45)), hdate.HDate(heb_date=hdate.HebrewDate(5782, Months.AV, 7), hebrew=False))  # after midnight
]


@pytest.mark.parametrize("d, expected", get_heb_date_from_pydate_date)
def test_get_heb_date_from_pydate(d: datetime, expected: hdate.HDate):
    heb_date = get_hdate_from_pydate(d)
    assert heb_date.hdate == expected.hdate
