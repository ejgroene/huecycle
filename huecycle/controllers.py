from random import randint
from datetime import time, datetime
from clock import clock

HOUR = 3600

def turn_on_between(members, t_ons, t_offs):
    while True:
        t_on = t_ons()
        try: t_off = t_offs()
        except StopIteration: return
        if isinstance(t_on, datetime): t_on = t_on.time()
        if isinstance(t_off, datetime): t_off = t_off.time()
        # Ignore conection errors here? #TODO
        if t_on < t_off:
            if not t_on < clock.time() < t_off:
                print("Next ON:", t_on)
                yield t_on
                for light in members:
                    yield randint(1,60)
                    light.send(on=True)
            print("Next OFF:", t_off)
            yield t_off
            for light in members:
                yield randint(1,60)
                light.send(on=False)
        else:
            yield HOUR


from prototype import object
from autotest import autotest, any_number


cmds = []
@object
def mocktarget():
    def send(self, on=None):
        cmds.append(on)
    def name(self):
        return "mock light"
        cmds
    return locals()

def mockdawns():
    yield     time(          8,0o4,00)
    yield datetime(2000,1,1, 8,0o5,00)
    yield     time(          8,0o6,00)

@autotest
def TurnOnAtDawnForAtLeast5Min():
    clock.set(datetime(2010,1,1, 7,00))
    c = turn_on_between([mocktarget], lambda: time(8,00), mockdawns().__next__)
    ts = list(c)
    assert ts[0] == time(8,00), ts[0]
    assert 1 <= ts[1] <= 60
    assert ts[2] == time(8,0o4), ts[2]
    assert 1 <= ts[3] <= 60
    assert ts[4] == time(8,00), ts[4]
    assert 1 <= ts[5] <= 60
    assert ts[6] == time(8,0o5), ts[6]
    assert 1 <= ts[7] <= 60
    assert ts[8] == time(8,00), ts[8]
    assert 1 <= ts[9] <= 60
    assert ts[10] == time(8,0o6), ts[10]
    assert cmds == [True, False, True, False, True, False], cmds

@autotest
def SkipOnIfTimeWithinInterval():
    cmds[:] = []
    clock.set(datetime(2010,1,1, 8,0o1))
    c = turn_on_between([mocktarget], lambda: time(8,00), mockdawns().__next__)
    ts = list(c)
    assert ts == [time(8,0o4), any_number(1,60), time(8,0o5), any_number(1,60), time(8,0o6), any_number(1,60)]
    assert cmds == [False, False, False], cmds

@autotest
def SkipIfEndBeforeBeginAndWait():
    c = turn_on_between([mocktarget], lambda: time(9,00), mockdawns().__next__)
    ts = list(c)
    assert [HOUR, HOUR, HOUR] == ts, ts

@autotest
def GoToNextDayOnWhenTimeAfterOff():
    cmds[:] = []
    clock.set(datetime(2010,1,1, 9,00))
    c = turn_on_between([mocktarget], lambda: time(8,00), mockdawns().__next__)
    ts = list(c)
    assert ts == [time(8,00), any_number(1,60), time(8,0o4), any_number(1,60), time(8,00), any_number(1,60), time(8,0o5), any_number(1,60), time(8,00), any_number(1,60), time(8,0o6), any_number(1,60)], ts
    assert cmds == [True, False, True, False, True, False], cmds

@autotest
def WorkWithDatetime():
    cmds[:] = []
    clock.set(datetime(2010,1,1, 8,0o1))
    c = turn_on_between([mocktarget], lambda: datetime(2010,12,31, 8,00), mockdawns().__next__)
    ts = list(c)
    assert ts == [time(8,0o4), any_number(1,60), time(8,0o5), any_number(1,60), time(8,0o6), any_number(1,60)]
    assert cmds == [False, False, False], cmds
    
