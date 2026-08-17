import contextlib
from datetime import date, datetime, time, timedelta

from astral.sun import sun
from constant import JERUSALEM_CITY, TZ
from hdate import HDateInfo, HebrewDate, HolidayTypes, Months, converters as conv
from hdate.translator import context_language
from pytz import timezone

HDATE_LANGUAGES = {"eng": "en", "heb": "he"}
HOLIDAY_TYPES_OF_INTEREST = (HolidayTypes.YOM_TOV, HolidayTypes.MELACHA_PERMITTED_HOLIDAY)


@contextlib.contextmanager
def language(lang):
    """Scope hdate's output language to this block.

    hdate 1.x selects language through a process-wide ContextVar rather than a
    per-object flag, and it defaults to Hebrew. mastodon-py dispatches
    on_notification on a background thread, so a global set_language() call
    could let two concurrent mentions cross-contaminate each other's replies.
    A ContextVar token is per-context, so this is safe under concurrency.
    """
    token = context_language.set(HDATE_LANGUAGES[lang])
    try:
        yield
    finally:
        context_language.reset(token)


def get_current_state(today=None):
    if today is None:
        today = HDateInfo()
    rosh_hashana = HebrewDate(today.hdate.year, Months.TISHREI, 1)
    days_count = conv.gdate_to_jdn(today.gdate) - rosh_hashana.to_jdn() + 1
    total_days = HebrewDate.year_size(today.hdate.year)
    return int((days_count / total_days) * 100)


def get_midnight(reference_date, tz):
    midnight = datetime.combine(reference_date + timedelta(days=1), time())
    return timezone(tz).localize(midnight)


def is_past_tzet_hakohavim_and_before_midnight(now, tz="UTC"):
    s = sun(JERUSALEM_CITY.observer, date=now)
    return get_midnight(now.date(), tz=tz) > now > s["sunset"]


def get_hdate_from_pydate(now_tz=None) -> HDateInfo:
    if not now_tz:
        now_tz = datetime.now(timezone(TZ))
    if is_past_tzet_hakohavim_and_before_midnight(now_tz, tz=TZ):
        now_tz = now_tz + timedelta(days=1)
    return HDateInfo(date=now_tz.date())


def get_current_date(lang="eng", now_tz=None) -> str:
    with language(lang):
        return str(get_hdate_from_pydate(now_tz=now_tz).hdate)


def get_current_parashah(lang="eng", now_tz=None) -> str:
    with language(lang):
        return get_hdate_from_pydate(now_tz=now_tz).parasha


def get_upcoming_holiday(lang="eng", now_tz=None) -> tuple[str, int]:
    with language(lang):
        iter_date = get_hdate_from_pydate(now_tz=now_tz)
        days_delta = 0
        while True:
            holidays = [h for h in iter_date.holidays if h.type in HOLIDAY_TYPES_OF_INTEREST]
            if holidays:
                return str(holidays[0]), days_delta
            iter_date = iter_date.next_day
            days_delta += 1
