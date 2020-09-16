import datetime

import pytest
from tweepy import Status

from tweet_helper import should_tweet, is_holiday_tweeted_today, get_last_state


def get_status(text, created_at=None):
    _json = {"text": text}
    if created_at:
        _json['created_at'] = created_at.strftime("%a %b %d %H:%M:%S %Y")
    return Status().parse(object, _json)


should_tweet_test_data = [
    (2, 1, False),
    (2, 2, False),
    (100, 1, False),
    (2, 3, True),
    (100, 0, True),
]

is_holiday_tweeted_today_test_data = [
    ([get_status(text="Happy Hanukkah!", created_at=datetime.datetime.today())], "Hanukkah", True),
    ([get_status(text="Happy Hanukkah!", created_at=datetime.datetime.today() - datetime.timedelta(days=1))], "Hanukkah", False),
    ([get_status(text="Happy Pesach!", created_at=datetime.datetime.today())], "Hanukkah", False),
]

get_last_state_test_data = [
    ([get_status(text="░" * 20 + " 0%")], 0),
    ([get_status(text="░" * 20 + " 0%")], 0),
    ([get_status(text="░" * 10 + "▓" * 10 + " 50%")], 50),
    ([get_status(text="▓" * 20 + " 100%")], 100),
    ([get_status(text="Something else on my mind"), get_status(text="░" * 20 + " 0%")], 0),
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
