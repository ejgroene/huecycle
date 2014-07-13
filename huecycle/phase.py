from misc import autostart, autotest, interpolate
from datetime import datetime, time

def datetime2hours(dt):
    return dt.hour + dt.minute / 60. + dt.second / 3600.

@autostart
def phase(d0, d1, curve, r0, r1):
    """Coroutine mapping domain (d0,d1) to range (r0,r1), allowing func to alter the curve."""
    if isinstance(d0, (datetime,time)):
        d0 = datetime2hours(d0)
    if isinstance(d1, (datetime, time)):
        d1 = datetime2hours(d1)
    if d1 < d0:
        d1 += 24.
    t = yield
    while True:
        if t is None:
            t = datetime.now()
        h = t.hour + t.minute / 60. + t.second / 3600.
        if h < d0:
            h += 24.
        if not d0 <= h <= d1:
            return
        f0 = (h - d0) / (d1 - d0)
        f1 = curve.send(f0)
        t = yield int(0.5 + r0 + f1 * (r1 - r0))


@autostart
def unity():
    x = None
    while True:
        x = yield x

@autotest
def CurrentTimeWhenNoneGiven():
    p = phase(8, 22, unity(), 1000, 9000)
    x = p.next()
    assert 1000 < x < 9000, x

@autotest
def AcceptDateTime():
    p = phase(time(8), time(22), unity(), 1000, 9000)
    x = p.next()
    assert 1000 < x < 9000, x
    p = phase(datetime(2014,6,22,8), datetime(2014,6,22,22), unity(), 1000, 9000)
    x = p.next()
    assert 1000 < x < 9000, x
    
@autotest
def NightlyHours():
    p = phase(22, 8, unity(), 1000, 9000)
    x = p.send(time(22))
    assert x == 1000, x
    x = p.send(time(23,59,59))
    assert x == 2600, x
    x = p.send(time( 0,00,01))
    assert x == 2600, x
    x = p.send(time( 7,59,59))
    assert x == 9000, x
    x = p.send(time( 8,00,00))
    assert x == 9000, x
    try:
        p.send(time( 8,00,01))
        assert False
    except StopIteration:
        pass

@autotest
def Interpolate():
    p = phase(7, 23, unity(), 1000, 9000)
    x = p.send(time(7))
    assert x == 1000, x
    x = p.send(time(23))
    assert x == 9000, x
    x = p.send(time(15))
    assert x == 5000, x
    x = p.send(time(15, 15))
    assert x == 5125, x
    x = p.send(time(15, 15, 21))
    assert x == 5128, x
    x = p.send(time(15, 15, 21))
    assert type(x) == int, x

@autotest
def CallMapping():
    fs = []
    @autostart
    def f():
        x = 0.
        while True: 
            x = yield x + 0.5
            fs.append(x)
    p = phase(8, 22, f(), 2000, 6000)
    x = p.send(time(8))
    assert x == 4000, x
    assert fs == [0.0], fs
    x = p.send(time(15))
    assert x == 6000, x
    assert fs == [0.0, 0.5], fs
    x = p.send(time(22))
    assert x == 8000, x
    assert fs == [0.0, 0.5, 1.0], fs

@autotest
def Stop():
    p = phase(9, 21, unity(), 0, 0)
    try:
        p.send(time(8,59,59))
        assert False
    except StopIteration:
        pass
    try:
        p.send(time(21,00,01))
        assert False
    except StopIteration:
        pass

