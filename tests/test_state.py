import hdate
import pytest
from hdate.htables import Months

from hypb.dates_helper import get_current_state

current_state_test_data = [
    (hdate.HDate(heb_date=hdate.HebrewDate(year=5780, month=Months.TISHREI, day=1)), 0),
    (hdate.HDate(heb_date=hdate.HebrewDate(year=5779, month=Months.ELUL, day=29)), 100),
    (hdate.HDate(heb_date=hdate.HebrewDate(year=5780, month=Months.NISAN, day=1)), 50),
    (hdate.HDate(heb_date=hdate.HebrewDate(year=5780, month=Months.ELUL, day=29)), 100),  # Shana Me'uberet
    (hdate.HDate(heb_date=hdate.HebrewDate(year=5779, month=Months.NISAN, day=1)), 54),  # Shana Me'uberet
]


@pytest.mark.parametrize("today,expected", current_state_test_data)
def test_current_state(today, expected):
    assert get_current_state(today) == expected
