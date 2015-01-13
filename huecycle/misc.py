import rfc822
from requests import put, get
from json import dumps

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

def autotest(f):
    print "%s.%s" % (f.__module__, f.__name__),
    f()
    print " Ok."

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
