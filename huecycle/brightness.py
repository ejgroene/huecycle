from datetime import time
from clock import clock
from phase import phase, sinus
from misc import autostart

@autostart
def brightness_cycle(t_wake, t_sleep, f):
    t = yield
    while True:
        p = phase(t_wake(), t_sleep(), f, 0, 255)
        try:
            while True:
                t = yield p.send(t)
        except StopIteration:
            t = yield 0



from autotest import autotest

@autotest
def CreateCycle():
    bri = brightness_cycle(lambda: time(7), lambda: time(23), sinus())

    b = bri.send(time(15,00))
    assert b == 255

    b = bri.send(time(7,00))
    assert b == 0, b

    b = bri.send(time(7,01))
    assert b == 1, b

    clock.set(time(15,00))
    b = bri.next()
    assert b == 255, b

    clock.set(time(22,59))
    b = bri.next()
    assert b == 1, b

    clock.set(time(23,00))
    b = bri.next()
    assert b == 0, b

    clock.set(time(23,01))
    b = bri.next()
    assert b == 0, b

    clock.set(time(23,59))
    b = bri.send(None)
    assert b == 0, b

    clock.set(time(0,01))
    b = bri.next()
    assert b == 0, b

    b = bri.send(time(0,01))
    assert b == 0, b

    b = bri.send(time(6,59))
    assert b == 0, b

    b = bri.send(time(7,01))
    assert b == 1, b

    b = bri.send(time(15,00))
    assert b == 255, b
