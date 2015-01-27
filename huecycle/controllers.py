from random import randint
from datetime import time, datetime, timedelta, date
from clock import clock
from misc import autostart

def turn_on_between(members, t_ons, t_offs):
    while True:
        t_on = clock.nexttime(t_ons())
        t_off = clock.nexttime(t_offs())
        if t_off > t_on + timedelta(minutes=5):
            print "Next ON:", t_on
            yield t_on
            for light in members:
                yield randint(1,60)
                light.turn_on(True)
            print "Next OFF:", t_on
            yield t_off
            for light in members:
                yield randint(1,60)
                light.turn_on(False)
        yield 4 * 3600


from prototype import object
from autotest import autotest

cmds = []
@object
def mocktarget(self):
    def turn_on(self, on):
        cmds.append(on)
    def name(self):
        return "mock light"
        cmds

@autotest
def TurnOnAtDawnForAtLeast5Min():
    def mockdawns():
        yield datetime(2000,1,1,8,05,01) # turn on at 8 for 5 min
        yield     time(         8,04,59) # do not turn on
        yield datetime(2000,1,1,8,06,02) # turn on
    c = turn_on_between([mocktarget], lambda: time(8,00), mockdawns().next)
    clock.set(datetime(2010,1,1, 7,00))
    dt = c.next()
    assert dt == datetime(2010,1,1, 8,00), dt

    dt = c.next()
    assert 1 <= dt <= 60

    dt = c.next()
    assert dt == datetime(2010,1,1, 8,05,01), dt

    dt = c.next()
    assert 1 <= dt <= 60

    dt = c.next()
    assert dt == 4 * 3600

    dt = c.next()
    assert dt == 4 * 3600

    dt = c.next()
    assert dt == datetime(2010,1,1, 8,00), dt

    dt = c.next()
    assert 1 <= dt <= 60

    dt = c.next()
    assert dt == datetime(2010,1,1, 8,06,02), dt

    dt = c.next()
    assert 1 <= dt <= 60

    dt = c.next()
    assert dt == 4 * 3600

    assert list(c) == [] # no more events
    assert cmds == [True, False, True, False], cmds

