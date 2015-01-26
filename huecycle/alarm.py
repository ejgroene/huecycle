from datetime import datetime, timedelta, time
from time import sleep
from misc import autostart
from sched import scheduler as Scheduler
from threading import Thread

FALL_OF_SAURON = datetime(1419, 03, 25, 0, 0, 0, 0)
DEFAULT_PRIO = 1

def fourth_age(shire_time=None):
    return ((shire_time or datetime.now()) - FALL_OF_SAURON).total_seconds()

def alarm(*observers):
    scheduler = Scheduler(fourth_age, sleep)
    for observer in observers:
        t = observer.next()
        add_timer(t, scheduler, observer)
    tread = Thread(None, scheduler.run)
    tread.daemon = True
    tread.start()
    return scheduler

def add_timer(t, scheduler, observer):
    if isinstance(t, time):
        date = datetime.now()
        if t < date.time():
            date += timedelta(days=1)
        t = datetime.combine(date, t)
    if isinstance(t, datetime):
        t = fourth_age(t)
        f = scheduler.enterabs
    else:
        f = scheduler.enter
    f(t, DEFAULT_PRIO, dispatch, (scheduler, observer))

def dispatch(scheduler, observer):
    try:
        t = observer.send(datetime.now())
    except StopIteration:
        return
    add_timer(t, scheduler, observer)
    

from misc import autotest

@autotest
def SetToNextTimeWhenNoDate():
    def observer1():
        yield time(23,59) # must be today
    def observer2():
        yield time( 0, 1) # must be tomorrow
    scheduler = alarm(observer1(), observer2())
    q = scheduler.queue
    print q
    t = datetime.combine(datetime.today(), time(23,59))
    assert q[0].time == fourth_age(t)
    t = datetime.combine(datetime.today()+timedelta(days=1), time( 0, 1))
    assert q[1].time == fourth_age(t)

@autotest
def SetAbsoluteDate():
    v = []
    def observer():
        t = yield datetime.now() + timedelta(seconds=0.1)
        v.append(t)
        t = yield datetime.now() + timedelta(seconds=0.05)
        v.append(t)
    a = alarm(observer())
    t0 = datetime.now()
    while not v: pass
    assert 0.09 < (v.pop() - t0).total_seconds() < 0.11 
    t0 = datetime.now()
    while not v: pass
    assert 0.045 < (v.pop() - t0).total_seconds() < 0.055 
    assert v == []

@autotest
def SetAlarmFromYieldValue():
    v = []
    def observer(v):
        v.append((yield 0.1))
        v.append((yield 0.2))
    t0 = datetime.now()
    a = alarm(observer(v))
    assert v == [], v
    while not v: pass
    assert 0.09 < (v.pop() - t0).total_seconds() < 0.11 
    t0 = datetime.now()
    while not v: pass
    assert 0.19 < (v.pop() - t0).total_seconds() < 0.21 
    assert v == []

@autotest
def SetAlarmInitialAlarm():
    v = []
    def observer():
        t = yield 0.1
        v.append(t)
    t0 = datetime.now()
    a = alarm(observer())
    assert v == [], v
    while not v: pass
    assert 0.09 < (v.pop() - t0).total_seconds() < 0.11 
    assert v == []

