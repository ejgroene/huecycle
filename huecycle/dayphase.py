from misc import autotest, autostart, interpolate
from datetime import datetime
from math import sin, pi, exp, copysign

def dayfactor(start, end, t):
    if start <= t <= end:
        return interpolate(start, end, t, 0.0, pi)
    return interpolate(end, start + 24, t + (24 if t < start else 0), pi, 2 * pi)

@autostart
def dayphase(start, end, boost=None):
    t = yield
    c = 1. - exp(-boost) if boost else None
    while True:
        if t is None:
            now = datetime.now()
            t = now.hour + now.minute/60.
        factor = dayfactor(start, end, t)
        angle = sin(factor)
        phase = copysign((1. - exp(-boost * abs(angle))) / c if boost else angle, angle)
        t = yield phase

@autotest
def testSinusPhase():
    p = dayphase(7, 23)
    f = p.send( 7)
    assert -0.0001 <  f < 0.0001, f
    f = p.send(11.)
    assert  0.7071 <  f < 0.7072, f
    f = p.send(15)
    assert  0.9999 <  f < 1.0001, f
    f = p.send(19)
    assert  0.7071 <  f < 0.7072, f
    f = p.send(23)
    assert -0.0001 <  f < 0.0001, f
    f = p.send( 1)
    assert  0.7071 < -f < 0.7072, f
    f = p.send( 3)
    assert  0.9999 < -f < 1.0001, f
    f = p.send( 5)
    assert  0.7071 < -f < 0.7072, f

@autotest
def testStretchPhase():
    p = dayphase(8, 22, boost=1.)
    f = p.send( 8)
    assert -0.0001 <  f < 0.0001, f
    f = p.send(11.5)
    assert  0.8019 <  f < 0.8020, f
    f = p.send(15)
    assert  0.9999 <  f < 1.0001, f
    f = p.send(18.5)
    assert  0.8019 <  f < 0.8020, f
    f = p.send(22)
    assert -0.0001 <  f < 0.0001, f
    f = p.send(0.5)
    assert  0.8019 < -f < 0.8020, f
    f = p.send(03)
    assert  0.9999 < -f < 1.0001, f
    f = p.send(5.5)
    assert  0.8019 < -f < 0.8020, f

@autotest
def testTime():
    p = dayphase(7, 23)
    f = p.next()
    assert -1 <= f <= 1, f
