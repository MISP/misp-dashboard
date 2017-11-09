import datetime

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

def getDateStrFormat(date):
    return str(date.year)+str(date.month).zfill(2)+str(date.day).zfill(2)
