from random import randint
from datetime import time, datetime, timedelta
from misc import autostart

def switch_group_randomly(members, next_time, switch):
    while True:
        t_next = next_time()
        print "Next switch:", "ON" if switch else "OFF", t_next
        yield t_next
        for light in members:
            print "Turning:", "ON" if switch else "OFF", light.name()
            light.turn_on(switch)
            yield randint(1, 60)

def dawn_on(members, next_dawn, t_wake):
    while True:
        t_next_dawn_end = next_dawn()
        if t_next_dawn_end > t_wake + timedelta(minutes=5):
            yield t_wake
            yield randint(1,60)

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
        yield datetime(2000,1,1,8,04,59) # do not turn on
        yield datetime(2000,1,1,8,05,01) # turn on
    c = dawn_on([mocktarget], mockdawns().next, datetime(2000,1,1,8,00))
    dt = c.next().time()
    assert dt == time(8,00), dt
    dt = c.next()
    assert 1 <= dt <= 60
    dt = c.next().time()
    assert dt == time(8,00), dt
    dt = c.next()
    assert 1 <= dt <= 60
    assert list(c) == [] # no more events

@autotest
def TestTurnOffLights():
    mocktarget2 = mocktarget()
    def mockrise():
        yield time(7,56)
        yield time(8,00)
    on = switch_group_randomly([mocktarget, mocktarget2], mockrise().next, True)

    dt = on.send(None)
    assert cmds == []
    assert dt == time(7,56), dt

    dt = on.send(None)
    assert cmds == [True]
    assert 1 <= dt <= 60, dt

    dt = on.send(None)
    assert cmds == [True, True], cmds
    assert 1 <= dt <= 60, dt

    dt = on.send(None)
    assert cmds == [True, True], cmds
    assert dt == time(8,00), dt

