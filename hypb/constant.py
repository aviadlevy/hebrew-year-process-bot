import os

from astral import LocationInfo

PROGRESS_BAR_WIDTH = 15
EMPTY_SYMBOL = "░"
PROGRESS_SYMBOL = "▓"


TZ = "Asia/Jerusalem"
JERUSALEM_CITY = LocationInfo(name="Jerusalem", region="Israel", timezone=TZ, latitude=31.783333333333335, longitude=35.2)

TISHREY = 7


TWITTER_USER_ID = 1099727648471871490
MASTODON_USER_ID = os.environ["MASTODON_USER_ID"]
