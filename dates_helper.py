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


def get_holiday(date=dates.HebrewDate.today()):
    """
    If not fast today, check if tomorrow is a holiday

    :param date: the date to check. typeof `dates.HebrewDate` from `pyluach`
    :return: tuple (name => string, is_holiday => bool) or None if no holiday
    """
    fast_table = hebrewcal._fast_day_table(date.year)
    if date in fast_table:
        return fast_table[date], False
    holiday = hebrewcal.holiday(date + 1, israel=True)
    if holiday:
        return holiday, True
    return None, None
