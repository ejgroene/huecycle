from datetime import datetime, timedelta
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

def add_timer(t, scheduler, observer):
    if isinstance(t, datetime):
        scheduler.enterabs(fourth_age(t), DEFAULT_PRIO, dispatch, (scheduler, observer))
    else:
        scheduler.enter(t, DEFAULT_PRIO, dispatch, (scheduler, observer))

def dispatch(scheduler, observer):
    try:
        t = observer.send(datetime.now())
    except StopIteration:
        return
    add_timer(t, scheduler, observer)
    

from misc import autotest

@autotest
def TestSetAlarmInitialAlarm():
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

@autotest
def TestSetAlarmFromYieldValue():
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
def TestSetAbsoluteDate():
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
