import pytest
from pyluach import dates

from dates_helper import get_current_state, get_holiday

current_state_test_data = [
    (dates.HebrewDate(year=5780, month=7, day=1), 0),
    (dates.HebrewDate(year=5779, month=6, day=29), 100),
    (dates.HebrewDate(year=5779, month=1, day=1), 50),
    (dates.HebrewDate(year=5780, month=6, day=29), 100),  # Shana Me'uberet
    (dates.HebrewDate(year=5780, month=1, day=1), 54),  # Shana Me'uberet
]

holiday_test_data = [
    (dates.HebrewDate(year=5780, month=7, day=9), ("Yom Kippur", True)),  # is holiday tomorrow
    (dates.HebrewDate(year=5780, month=7, day=1), ("Rosh Hashana", True)),  # second day of Rosh Hashana
    (dates.HebrewDate(year=5780, month=5, day=9), ("9 of Av", False)),  # 9 av - fast
    (dates.HebrewDate(year=5780, month=2, day=12), (None, None)),  # no holiday
]


@pytest.mark.parametrize("today,expected", current_state_test_data)
def test_current_state(today, expected):
    assert get_current_state(today) == expected


@pytest.mark.parametrize("today,expected", holiday_test_data)
def test_get_holiday(today, expected):
    assert get_holiday(today) == expected
