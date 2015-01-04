from time import sleep, time
from datetime import datetime

def clock(T, *observers):
    while True:
        t = datetime.now().time()
        for observer in observers:
            observer.send(t)
        sleep(T)
        yield



from misc import autotest, autostart

@autostart
def observer(v):
    while True:
        v.append((yield))

@autotest
def TickFormat():
    from datetime import time
    values = []
    o = observer(values)
    c = clock(1, o)
    t_soll = datetime.now().time()
    c.next()
    assert values, values
    t = values[0]
    assert isinstance(t, time), type(t)
    assert t.hour == t_soll.hour, (t, t_soll)
    assert t.minute == t_soll.minute, (t, t_soll)
    assert t.second == t_soll.second, (t, t_soll)

@autotest
def TickIntervalSmall():
    c = clock(0.1)
    t0 = time()
    c.next()
    t1 = time()
    c.next()
    t2 = time()
    assert 0.09 < t1 - t0 < 0.11, t1 - t0
    assert 0.09 < t2 - t1 < 0.11, t2 - t1

def TickIntervalStandard():
    c = clock(1)
    t0 = time()
    c.next()
    t1 = time()
    c.next()
    t2 = time()
    assert 0.9 < t1 - t0 < 1.1, t1 - t0
    assert 0.9 < t2 - t1 < 1.1, t2 - t1
