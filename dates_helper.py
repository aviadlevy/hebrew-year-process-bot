import datetime

from pyluach import dates, hebrewcal


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


def get_holiday():
    return hebrewcal.holiday(dates.HebrewDate.today() + 1, israel=True)
