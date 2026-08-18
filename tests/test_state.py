import hdate
import pytest
from hdate import Months

from hypb.dates_helper import get_current_state

current_state_test_data = [
    (hdate.HDateInfo(date=hdate.HebrewDate(year=5780, month=Months.TISHREI, day=1)), 0),
    (hdate.HDateInfo(date=hdate.HebrewDate(year=5779, month=Months.ELUL, day=29)), 100),
    (hdate.HDateInfo(date=hdate.HebrewDate(year=5780, month=Months.NISAN, day=1)), 50),
    (hdate.HDateInfo(date=hdate.HebrewDate(year=5780, month=Months.ELUL, day=29)), 100),  # Shana Me'uberet
    (hdate.HDateInfo(date=hdate.HebrewDate(year=5779, month=Months.NISAN, day=1)), 54),  # Shana Me'uberet
]


@pytest.mark.parametrize("today,expected", current_state_test_data)
def test_current_state(today, expected):
    assert get_current_state(today) == expected


def test_current_state_defaults_to_today():
    """get_current_state() with no argument must build HDateInfo() itself.

    Every other test in this file injects an HDateInfo, leaving the
    `today is None` branch -- the actual production path -- unexercised. The
    exact percentage changes daily, so only assert it's a plausible one.
    """
    result = get_current_state()
    assert isinstance(result, int)
    assert result in range(0, 101)
