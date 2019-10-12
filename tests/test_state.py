import pytest
from pyluach import dates

from dates_helper import get_current_state

current_state_test_data = [
    (dates.HebrewDate(year=5780, month=7, day=1), 0),
    (dates.HebrewDate(year=5779, month=6, day=29), 100),
    (dates.HebrewDate(year=5779, month=1, day=1), 50),
    (dates.HebrewDate(year=5780, month=6, day=29), 100),  # Shana Me'uberet
    (dates.HebrewDate(year=5780, month=1, day=1), 54),  # Shana Me'uberet
]


@pytest.mark.parametrize("today,expected", current_state_test_data)
def test_current_state(today, expected):
    assert get_current_state(today) == expected
