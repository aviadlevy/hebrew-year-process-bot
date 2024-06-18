import datetime

from dates_helper import get_current_date, get_current_parashah, get_upcoming_yom_tov


def get_eng_date():
    return f"The date is:\n{get_current_date(lang='eng')}"


def get_heb_date():
    return f"התאריך הוא:\n{get_current_date(lang='heb')}"


def get_eng_parashah():
    return f"The Parashah is {get_current_parashah(lang='eng')}"


def get_heb_parashah():
    return f"פרשת השבוע היא פרשת {get_current_parashah(lang='heb')}"


def get_eng_yom_tov():
    upcoming_yom_tov = get_upcoming_yom_tov(lang='eng')
    days_delta = (upcoming_yom_tov.gdate - datetime.datetime.now().date()).days
    return f"The upcoming Yom Tov is {upcoming_yom_tov.holiday_description} and it'll arrive in {days_delta} days"


def get_heb_yom_tov():
    upcoming_yom_tov = get_upcoming_yom_tov(lang='heb')
    days_delta = (upcoming_yom_tov.gdate - datetime.datetime.now().date()).days
    return f"החג הקרוב הוא {upcoming_yom_tov.holiday_description}. החג יגיע בעוד {days_delta} ימים"


MESSAGES = {
    "date": {
        "heb": get_heb_date,
        "eng": get_eng_date
    },
    "parashah": {
        "heb": get_heb_parashah,
        "eng": get_eng_parashah
    },
    "yom_tov": {
        "heb": get_heb_yom_tov,
        "eng": get_eng_yom_tov
    }
}
