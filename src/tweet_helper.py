import datetime
import re

from constant import EMPTY_SYMBOL, PROGRESS_SYMBOL, PROGRESS_BAR_WIDTH
from src.lang import MESSAGES


def get_last_state(tweets):
    for tweet in tweets:
        match = re.match(r'^[%s%s]{%d}\s(\d+)' % (EMPTY_SYMBOL, PROGRESS_SYMBOL, PROGRESS_BAR_WIDTH) + "%$",
                         tweet.text)
        if match:
            return int(match.group(1))


def should_tweet(last_state, current_state):
    return current_state > last_state or (last_state == 100 and current_state == 0)


def is_holiday_tweeted_today(timeline, holiday):
    return len([t for t in timeline if
                t.created_at.date() == datetime.datetime.today().date() and "%s" % holiday in t.text]) > 0


def get_text_to_reply(text):
    if "date" in text:
        return MESSAGES["date"]["eng"]()
    elif "תאריך" in text:
        return MESSAGES["date"]["heb"]()
    elif "parasha" in text:
        return MESSAGES["parashah"]["eng"]()
    elif any(x in text for x in ["פרשה", "פרשת"]):
        return MESSAGES["parashah"]["heb"]()