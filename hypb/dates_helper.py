from datetime import date, datetime, time, timedelta

from astral.sun import sun
from constant import JERUSALEM_CITY, TZ
from hdate import HDate, HebrewDate, converters as conv
from hdate.htables import Months
from pytz import timezone


def get_current_state(today=HDate()):
    rosh_hashana = HebrewDate(today.hdate.year, Months.TISHREI, 1)
    days_count = conv.gdate_to_jdn(today.gdate) - conv.hdate_to_jdn(rosh_hashana) + 1
    total_days = today.year_size()
    return int((days_count / total_days) * 100)


def get_midnight(tz):
    midnight = datetime.combine(date.today() + timedelta(days=1), time())
    return timezone(tz).localize(midnight)


def is_past_tzet_hakohavim_and_before_midnight(now, tz="UTC"):
    s = sun(JERUSALEM_CITY.observer, date=now)
    return get_midnight(tz=tz) > now > s["sunset"]


def get_current_date(lang="eng") -> str:
    return get_hdate_from_pydate(lang=lang).hebrew_date


def get_hdate_from_pydate(now_tz=datetime.now(timezone(TZ)), lang="eng") -> HDate:
    heb_date = HDate(gdate=now_tz, hebrew=lang == "heb")
    if is_past_tzet_hakohavim_and_before_midnight(now_tz, tz=TZ):
        now_tz = now_tz + timedelta(days=1)
        heb_date = HDate(gdate=now_tz, hebrew=lang == "heb")
    return heb_date


def get_current_parashah(lang="eng") -> str:
    return get_hdate_from_pydate(lang=lang).parasha


def get_upcoming_yom_tov(lang="eng") -> str:
    return get_hdate_from_pydate(lang=lang).upcoming_yom_tov
