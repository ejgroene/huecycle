from misc import autostart, autotest, interpolate
from datetime import datetime, time

@autostart
def phase(begin, end, f, lo, hi):
    if end < begin:
        end = end + 24.
    t = yield
    while True:
        h = t.hour + t.minute / 60. + t.second / 3600.
        if h < begin:
            h += 24.
        if not begin <= h <= end:
            return
        t = yield int(0.5 + interpolate(begin, end, f.send(h), lo, hi))

@autostart
def unity():
    x = None
    while True:
        x = yield x

@autotest
def testNightlyHours():
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
def testInterpolate():
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
def testCallMapping():
    @autostart
    def f():
        x = 0.
        while True: 
            x = yield x * 2.
    p = phase(8, 22, f(), 2000, 6000)
    x = p.send(time(8))
    assert x == 4286, x

@autotest
def testStop():
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

