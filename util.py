import datetime, time

ONE_DAY = 60*60*24

def getMonthSpan(date):
    ds = datetime.datetime(date.year, date.month, 1)
    dyear = 1 if ds.month+1 > 12 else 0
    dmonth = -12 if ds.month+1 > 12 else 0
    de = datetime.datetime(ds.year + dyear, ds.month+1 + dmonth, 1)

    delta = de - ds
    to_return = []
    for i in range(delta.days):
        to_return.append(ds + datetime.timedelta(days=i))
    return to_return

def getXPrevDaysSpan(date, days):
    de = date
    ds = de - datetime.timedelta(days=days)

    delta = de - ds
    to_return = []
    for i in range(delta.days+1):
        to_return.append(de - datetime.timedelta(days=i))
    return to_return

def getXPrevHoursSpan(date, hours):
    de = date
    de = de.replace(minute=0, second=0, microsecond=0)
    ds = de - datetime.timedelta(hours=hours)

    delta = de - ds
    to_return = []
    for i in range(0, int(delta.total_seconds()/3600)+1):
        to_return.append(de - datetime.timedelta(hours=i))
    return to_return

def getHoursSpanOfDate(date, adaptToFitCurrentTime=True, daySpanned=6):
    ds = date
    ds = ds.replace(hour=0, minute=0, second=0, microsecond=0)
    to_return = []
    now = datetime.datetime.now()
    for i in range(0, 24):
        the_date = ds + datetime.timedelta(hours=i)
        if the_date > now or the_date < now - datetime.timedelta(days=daySpanned): # avoid going outside
            continue
        to_return.append(the_date)
    return to_return

def getDateStrFormat(date):
    return str(date.year)+str(date.month).zfill(2)+str(date.day).zfill(2)

def getDateHoursStrFormat(date):
    return getDateStrFormat(date)+str(date.hour)

def getTimestamp(date):
    return int(time.mktime(date.timetuple()))
