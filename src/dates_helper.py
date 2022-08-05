from datetime import datetime, date, time, timedelta

from astral import LocationInfo
from astral.sun import sun
from pyluach import dates, hebrewcal, parshios
from pytz import timezone

from constant import JERUSALEM_CITY, TZ


def get_current_state(today=dates.HebrewDate.today()):
    days_count = 0
    total_days = 0
    # Tishrey and above
    if today.month >= 7:
        year = today.year
    else:
        year = today.year - 1
    # first from Tishrey to Adar
    for date in hebrewcal.Year(year).iterdates():
        if date.month == 1:
            break
        if date <= today:
            days_count += 1
        total_days += 1
    # then from Nissan to Elul
    for date in hebrewcal.Year(year + 1).iterdates():
        if date.month >= 7:
            continue
        if date <= today:
            days_count += 1
        total_days += 1
    return int((days_count / total_days) * 100)


def get_holiday(date=dates.HebrewDate.today()):
    """
    If not fast today, check if tomorrow is a holiday

    :param date: the date to check. typeof `dates.HebrewDate` from `pyluach`
    :return: tuple (name => string, is_holiday => bool) or None if no holiday
    """
    fast_day = hebrewcal.fast_day(date)
    if fast_day:
        return fast_day, False
    holiday = hebrewcal.holiday(date + 1, israel=True)
    if holiday:
        return holiday, True
    return None, None


def get_midnight(tz):
    midnight = datetime.combine(date.today() + timedelta(days=1), time())
    return timezone(tz).localize(midnight)


def is_past_tzet_hakohavim_and_before_midnight(now, tz="UTC"):
    s = sun(JERUSALEM_CITY.observer, date=now)
    return get_midnight(tz=tz) > now > s["sunset"]


def get_current_date(lang="eng") -> str:
    d = get_today_heb_date()
    if lang == "heb":
        return f"{d:%*d %*B %*Y}"
    else:
        return f"{d:%-d %B %Y}"


def get_today_heb_date():
    now_tz = datetime.now(timezone(TZ))
    d = get_heb_date_from_pydate(now_tz)
    return d


def get_heb_date_from_pydate(d: datetime):
    heb_date = dates.GregorianDate.from_pydate(d).to_heb()
    if is_past_tzet_hakohavim_and_before_midnight(d, tz=TZ):
        heb_date += 1
    return heb_date


def get_current_parashah(lang="eng") -> str:
    return parshios.getparsha_string(get_today_heb_date(), hebrew=(lang == "heb"))
