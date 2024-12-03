
from dates_helper import get_current_date, get_current_parashah, get_upcoming_holiday


def get_eng_date():
    return f"The date is:\n{get_current_date(lang='eng')}"


def get_heb_date():
    return f"התאריך הוא:\n{get_current_date(lang='heb')}"


def get_eng_parashah():
    return f"The Parashah is {get_current_parashah(lang='eng')}"


def get_heb_parashah():
    return f"פרשת השבוע היא פרשת {get_current_parashah(lang='heb')}"


def get_eng_yom_tov():
    upcoming_holiday, days_delta = get_upcoming_holiday(lang="eng")
    return f"The upcoming holiday is {upcoming_holiday.holiday_description} and it'll arrive in {days_delta} days"


def get_heb_yom_tov():
    upcoming_holiday, days_delta = get_upcoming_holiday(lang="heb")
    return f"החג הקרוב הוא {upcoming_holiday.holiday_description}. החג יגיע בעוד {days_delta} ימים"


MESSAGES = {
    "date": {"heb": get_heb_date, "eng": get_eng_date},
    "parashah": {"heb": get_heb_parashah, "eng": get_eng_parashah},
    "yom_tov": {"heb": get_heb_yom_tov, "eng": get_eng_yom_tov},
}
