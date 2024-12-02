import re

from constant import EMPTY_SYMBOL, PROGRESS_BAR_WIDTH, PROGRESS_SYMBOL
from lang import MESSAGES


def get_last_state(toots):
    """
    extract the last state from Mastodon

    :param toots: toots from Mastodon
    :return:
    """
    for toot in toots:
        match = re.match(r"^<p>[%s%s]{%d}\s(\d+)" % (EMPTY_SYMBOL, PROGRESS_SYMBOL, PROGRESS_BAR_WIDTH) + "%</p>$", toot["content"])  # noqa: UP031
        if match:
            return int(match.group(1))


def should_tweet(last_state, current_state):
    return current_state > last_state or (last_state == 100 and current_state == 0)  # noqa: PLR2004


def get_text_to_reply(text):
    if "date" in text:
        return MESSAGES["date"]["eng"]()
    elif "תאריך" in text:
        return MESSAGES["date"]["heb"]()
    elif "parasha" in text:
        return MESSAGES["parashah"]["eng"]()
    elif any(x in text for x in ["פרשה", "פרשת"]):
        return MESSAGES["parashah"]["heb"]()
    elif any(x in text for x in ["holiday", "yom tov"]):
        return MESSAGES["yom_tov"]["eng"]()
    elif any(x in text for x in ["חג", "יום טוב"]):
        return MESSAGES["yom_tov"]["heb"]()
