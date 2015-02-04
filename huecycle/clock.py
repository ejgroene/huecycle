from datetime import datetime, time, timedelta, date

class clock(object):

    def __init__(self):
        self.set()

    def set(self, t=None):
        self._d = t.date() if isinstance(t, datetime) else t if isinstance(t, date) else None
        self._t = t.time() if isinstance(t, datetime) else t if isinstance(t, time) else None

    def nexttime(self, h, m=0, s=0):
        if isinstance(h, datetime):
            if h.date() > self.date():
                return h
            tim = h.time()
        else:
            tim = h if isinstance(h, time) else time(h, m, s)
        day = self.date()
        if tim <= self.time():
            day += timedelta(days=1)
        return datetime.combine(day, tim)

    def date(self):
        return self._d or datetime.now().date()

    def time(self):
        return self._t or datetime.now().time()

    def now(self):
        return datetime.combine(self.date(), self.time())

clock = clock()

from autotest import autotest

@autotest
def ExpandTimeWithDay():
    t0 = datetime.now()
    t1 = clock.nexttime((t0 - timedelta(seconds=1)).time())
    assert t1 == t0 + timedelta(days=1, seconds=-1), (t1, t0)
    t0 = datetime.now()
    t1 = clock.nexttime(t0.time())
    assert t1 == t0 + timedelta(days=1), (t1, t0)
    t0 = datetime.now()
    t1 = clock.nexttime((t0 + timedelta(seconds=1)).time())
    assert t1 == t0 + timedelta(seconds=1), (t1, t0)
    clock.set(datetime(2411, 3, 25,  23, 59, 58))
    t1 = clock.nexttime(23,59,57)
    assert t1 == datetime(2411, 3, 26,  23, 59, 57), t1
    t1 = clock.nexttime(23,59,59)
    assert t1 == datetime(2411, 3, 25,  23, 59, 59), t1
    t1 = clock.nexttime( 0, 0, 0)
    assert t1 == datetime(2411, 3, 26,   0,  0,  0), t1
    t1 = clock.nexttime(datetime(4512, 12, 31, 23, 59, 57)) # don't get fooled if date is in future
    assert t1 == datetime(4512, 12, 31, 23, 59, 57), t1
    t1 = clock.nexttime(datetime(4512, 12, 31, 23, 59, 59)) # don't get fooled if date is in future
    assert t1 == datetime(4512, 12, 31, 23, 59, 59), t1
    t1 = clock.nexttime(datetime(1500, 12, 31, 23, 59, 57)) # don't get fooled if date is in past
    assert t1 == datetime(2411, 3, 26, 23, 59, 57), t1
    t1 = clock.nexttime(datetime(1500, 12, 31, 23, 59, 59)) # don't get fooled if date is in past
    assert t1 == datetime(2411, 3, 25, 23, 59, 59), t1

@autotest
def SetDateAndTime():
    clock.set(datetime(1634, 2, 23, 16, 59, 59))
    assert clock.now() == datetime(1634, 2, 23, 16, 59, 59)

@autotest
def SetDateOnly():
    clock.set(None)
    clock.set(date(1634, 2, 23))
    assert clock.date() ==  date(1634, 2, 23), clock.date()
    t0 = datetime.now().time()
    t  = clock.time()
    t1 = datetime.now().time()
    assert t0 < t < t1

@autotest
def SetDateOnlyWithZeroTime():
    clock.set(datetime(2301, 9, 15))
    assert clock.date() ==  date(2301, 9, 15), clock.date()
    t0 = datetime.now().time()
    t  = clock.time()
    t1 = datetime.now().time()
    assert t0 < t < t1

@autotest
def SetTimeOnly():
    clock.set(time(18,30))
    assert clock.date() == datetime.now().date(), clock.date()
    assert clock.time() == time(18,30)
