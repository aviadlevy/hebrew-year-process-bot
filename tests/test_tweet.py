import datetime

import pytest

from tweet_helper import should_tweet, is_holiday_tweeted_today, get_last_state

should_tweet_test_data = [
    (2, 1, False),
    (2, 2, False),
    (100, 1, False),
    (2, 3, True),
    (100, 0, True),
]

is_holiday_tweeted_today_test_data = [
    ([{"created_at": datetime.datetime.today(), "text": "Happy Holiday!"}], "Holiday", True),
    ([{"created_at": datetime.datetime.today() - datetime.timedelta(days=1), "text": "Happy Holiday!"}], "Holiday",
     False),
    ([{"created_at": datetime.datetime.today(), "text": "Happy Holiday1!"}], "Holiday", False),
]

get_last_state_test_data = [
    ([{"text": "░" * 20 + " 0%"}], 0),
    ([{"text": "░" * 10 + "▓" * 10 + " 50%"}], 50),
    ([{"text": "▓" * 20 + " 100%"}], 100),
    ([{"text": "Something else on my mind"}, {"text": "░" * 20 + " 0%"}], 0),
]


@pytest.mark.parametrize("last_state, current_state, expected", should_tweet_test_data)
def test_should_tweet(last_state, current_state, expected):
    assert should_tweet(last_state, current_state) == expected


@pytest.mark.parametrize("timeline, holiday, expected", is_holiday_tweeted_today_test_data)
def test_is_holiday_tweeted_today(timeline, holiday, expected):
    assert is_holiday_tweeted_today(timeline, holiday) == expected


@pytest.mark.parametrize("tweets, expected", get_last_state_test_data)
def test_get_last_state(tweets, expected):
    assert get_last_state(tweets) == expected
