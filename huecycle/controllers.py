def turn_on_at_dawn(lamp, t_wake, next_dawn):
    while True:
        t_dawn = next_dawn()
        if t_wake < t_dawn:
            print "Next ON:", t_wake
            yield t_wake
            lamp.send(dict(on=True))
        else:
            yield 12 * 3600

def turn_on_at_dusk(lamp, t_sleep, next_dusk):
    while True:
        t_dusk = next_dusk()
        if t_dusk < t_sleep:
            print "Next ON:", t_dusk
            yield t_dusk
            lamp.send(dict(on=True))
        else:
            yield 12 * 3600

def turn_off(lamp, next_time):
    while True:
        t_next = next_time()
        print "Next OFF:", t_next
        yield t_next
        lamp.send(dict(on=False))

from misc import autotest, autostart
from datetime import time

@autotest
def TestTurnOffLightsAfterSunRise():
    cmds = []
    @autostart
    def mocklamp():
        while True: cmds.append((yield))
    def mockrise():
        yield time(7,56) # lights must turn off after sun rise
        yield time(8,00) # lights must turn off after sun rise
    on = turn_off(mocklamp(), mockrise().next)

    dt = on.send(None)
    assert cmds == []
    assert dt == time(7,56), dt

    dt = on.send(None)
    assert cmds.pop() == {"on": False}
    assert dt == time(8,00), dt

@autotest
def TestTurnOnAtDawn():
    cmds = []
    @autostart
    def mocklamp():
        while True: cmds.append((yield))
    def mock_dawn():
        yield time(7,56)
        yield time(7,54)
        yield time(6,00)
        yield time(9,00)
        yield time(1,00)
    on = turn_on_at_dawn(mocklamp(), time(7,55), mock_dawn().next)
    dt = on.send(None)
    assert dt == time(7,55), dt
    assert cmds == []

    dt = on.send(None)
    assert dt == 12 * 3600, dt
    assert cmds.pop() == {"on": True}

    dt = on.send(None)
    assert dt == 12 * 3600, dt
    assert cmds == []

    dt = on.send(None)
    assert dt == time(7,55), dt
    assert cmds == []
    
    dt = on.send(None)
    assert dt == 12 * 3600, dt
    assert cmds.pop() == {"on": True}

@autotest
def TestTurnOnAtDusk():
    cmds = []
    @autostart
    def mocklamp():
        while True: cmds.append((yield))
    def mock_dusk():
        yield time(23,00)
        yield time(22,30)
        yield time(18,00)
        yield time(16,00)
        yield time(23,30)
    on = turn_on_at_dusk(mocklamp(), time(22,45), mock_dusk().next)
    dt = on.send(None)
    assert cmds == []
    assert dt == 12 * 3600, dt
    
    dt = on.send(None)
    assert cmds == []
    assert dt == time(22,30), dt

    dt = on.send(None)
    assert cmds.pop() == {"on": True}
    assert dt == time(18,00), dt

    dt = on.send(None)
    assert cmds.pop() == {"on": True}
    assert dt == time(16,00), dt

    dt = on.send(None)
    assert cmds.pop() == {"on": True}
    assert dt == 12 * 3600, dt

