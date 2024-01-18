from dates_helper import get_current_date, get_current_parashah


def get_eng_date():
    return f"The date is:\n{get_current_date(lang='eng')}"


def get_heb_date():
    return f"התאריך הוא:\n{get_current_date(lang='heb')}"


def get_eng_parashah():
    return f"The Parashah is {get_current_parashah(lang='eng')}"


def get_heb_parashah():
    return f"פרשת השבוע היא פרשת {get_current_parashah(lang='heb')}"


MESSAGES = {
    "date": {
        "heb": get_heb_date,
        "eng": get_eng_date
    },
    "parashah": {
        "heb": get_heb_parashah,
        "eng": get_eng_parashah
    }
}
