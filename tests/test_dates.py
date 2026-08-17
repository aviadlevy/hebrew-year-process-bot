from datetime import date, datetime

import hdate
import pytest
from hdate.htables import Months
from pytz import timezone

from hypb.constant import TZ
from hypb.dates_helper import (
    get_hdate_from_pydate,
    get_midnight,
    is_past_tzet_hakohavim_and_before_midnight,
)

get_heb_date_from_pydate_date = [
    (timezone(TZ).localize(datetime(2022, 8, 3, 18, 45)), hdate.HDate(heb_date=hdate.HebrewDate(5782, Months.AV, 6), hebrew=False)),  # before subset
    (timezone(TZ).localize(datetime(2022, 8, 3, 20, 45)), hdate.HDate(heb_date=hdate.HebrewDate(5782, Months.AV, 7), hebrew=False)),  # after sunset
    (timezone(TZ).localize(datetime(2022, 8, 4, 00, 45)), hdate.HDate(heb_date=hdate.HebrewDate(5782, Months.AV, 7), hebrew=False))  # after midnight
]


@pytest.mark.parametrize("d, expected", get_heb_date_from_pydate_date)
def test_get_heb_date_from_pydate(d: datetime, expected: hdate.HDate):
    heb_date = get_hdate_from_pydate(d)
    assert heb_date.hdate == expected.hdate


def test_is_past_tzet_uses_the_given_date_not_today():
    """A future evening after sunset is 'past tzet and before midnight'.

    get_midnight() used to build tomorrow's midnight from date.today(), so any
    reference date beyond tomorrow compared against the wrong boundary and
    returned False.
    """
    future_evening = timezone(TZ).localize(datetime(2027, 3, 1, 20, 45))
    assert is_past_tzet_hakohavim_and_before_midnight(future_evening, tz=TZ) is True


def test_get_midnight_is_relative_to_its_argument():
    midnight = get_midnight(date(2027, 3, 1), TZ)
    assert midnight == timezone(TZ).localize(datetime(2027, 3, 2, 0, 0))
