import rfc822
from requests import put, get
from json import dumps
from clock import clock

def autostart(f):
    def g(*args, **kwargs):
        h = f(*args, **kwargs)
        h.next()
        return h
    return g

def identify(f):
    def g(*args, **kwargs):
        h = f(*args, **kwargs)
        h.next()
        h.send(h)
        return h
    return g

def time822(s):
    return rfc822.mktime_tz(rfc822.parsedate_tz(s))

@autostart
def average():
    v = yield
    n = 1
    while True:
        v += yield v / n
        n += 1

def interpolate(lo, hi, x, lo2, hi2):
    return lo2 + (float(x) - lo) * (hi2 - lo2) / (hi - lo)

@autostart
def lamp(url):
    postfix = "/action" if "/groups/" in url else "/state"
    while True:
        kwargs = yield
        if not kwargs:
            yield get(url).json["state"]
            continue
        r = put(url + postfix, dumps(kwargs)).json
        if not "success" in r[0]:
            print r[0], kwargs
            if r[0]["error"]["type"] == 201:  # lamps are off
                continue

@autostart
def attenuator(light):
    ct, bri = 500, 0
    while True:
        args = yield
        if "ct" in args:
            args["ct"] = ct = ct + (args["ct"] - ct) / 10
        if "bri" in args:
            args["bri"] = bri = bri + (args["bri"] - bri) / 10
        light.send(args)

def hours(t):
    return t.hour + t.minute / 60. 


from datetime import datetime, timedelta
def find_next_change(g):
    t = clock.now()
    v = g.send(t)
    while True:
        yield t, v
        prev = v
        while v == prev:
            t += timedelta(seconds=1)
            v = g.send(t)


from autotest import autotest

@autotest
def FindNextChange():
    ts = []
    @autostart
    def src():
        ts.append((yield 1)) # t0
        ts.append((yield 1)) # t1
        ts.append((yield 2)) # t2
        ts.append((yield 2)) # t3
        ts.append((yield 2)) # t4
        ts.append((yield 3)) # t5
    t0 = clock.now()
    t1 = t0 + timedelta(seconds=1)
    t2 = t0 + timedelta(seconds=2)
    t3 = t0 + timedelta(seconds=3)
    t4 = t0 + timedelta(seconds=4)
    t5 = t0 + timedelta(seconds=5)
    t6 = t0 + timedelta(seconds=6)
    g = find_next_change(src())
    t, v = g.next()
    assert v == 1
    assert t0 <= t <= t1, (t0, t, t1)
    assert ts == [t], ts
    t, v = g.next()
    assert v == 2, v
    assert t1 <= t <= t3
    assert ts[-1] == t
    t, v = g.next()
    assert v == 3
    assert t4 <= t <= t6
    assert ts[-1] == t

@autotest
def FindNextChangeWithClockSet():
    @autostart
    def src():
        yield 3
        yield 3
        yield 5
        yield 3
        yield 3
        yield 3
        yield 7
    t = datetime(2020, 1, 1, 12, 00)
    clock.set(t)
    g = list(find_next_change(src()))
    assert g == [(t,3), (t+timedelta(seconds=1),5), (t+timedelta(seconds=2),3), (t+timedelta(seconds=5),7)], g


@autotest
def TimeDiff():
    from datetime import time
    td = hours(time(4)) - hours(time(3))
    assert td == 1., td
    td = hours(time(5)) - hours(time(3))
    assert td == 2.0, td
    td = hours(time(4,15)) - hours(time(3))
    assert td == 1.25, td
    td = hours(time(4)) - hours(time(3,15))
    assert td == 0.75, td
    td = hours(time(3)) - hours(time(3,15))
    assert td == -0.25, td

@autotest
def TestGetState():
    from config import LOCAL_HUE_API
    l = lamp(LOCAL_HUE_API + "/lights/1")
    state = l.next()
    assert state["on"] in (False, True), state

