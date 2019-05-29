import datetime
import time
from collections import defaultdict

ONE_DAY = 60*60*24

def getZrange(serv_redis_db, keyCateg, date, topNum, endSubkey=""):
    date_str = getDateStrFormat(date)
    keyname = "{}:{}{}".format(keyCateg, date_str, endSubkey)
    data = serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
    data = [ [record[0].decode('utf8'), record[1]] for record in data ]
    return data

def noSpaceLower(text):
    return text.lower().replace(' ', '_')

def push_to_redis_zset(serv_redis_db, mainKey, toAdd, endSubkey="", count=1):
    now = datetime.datetime.now()
    today_str = getDateStrFormat(now)
    keyname = "{}:{}{}".format(mainKey, today_str, endSubkey)
    serv_redis_db.zincrby(keyname, toAdd, count)

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


def sortByTrendingScore(toSort, topNum=5):
    scoredLabels = defaultdict(float)
    numDay = len(toSort)
    baseDecay = 1.0
    decayRate = lambda x: baseDecay*((numDay-x**2)/numDay)

    for i, arr in enumerate(toSort):
        timestamp = arr[0]
        dailyData = arr[1]
        for item in dailyData:
            label = item[0]
            occ = item[1]
            scoredLabels[label] += occ*decayRate(i)

    topList = [[l, s] for l, s in scoredLabels.items()]
    topList.sort(key=lambda x: x[1], reverse=True)
    topSet = [ l for l, v in topList[:topNum]]

    # now that we have the top, filter out poor scored elements
    topArray = []
    for arr in toSort:
        timestamp = arr[0]
        dailyData = arr[1]
        topDailyArray = list(filter(lambda item: (item[0] in topSet), dailyData))
        dailyCombi = [timestamp, topDailyArray]
        topArray.append(dailyCombi)

    return topArray
