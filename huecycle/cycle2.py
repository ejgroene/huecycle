#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sunphase import location
from datetime import time
from config import LOCAL_HUE_API
from controllers import turn_on_between
from alarm import alarm
from config import BRI_SINUS_CHARGE
from phase import phase, sinus, charge
from datetime import datetime, timedelta
from time import sleep
from clock import clock

from bridge import bridge
from tap import tap_control

clock.set()

local_bridge = bridge(baseurl=LOCAL_HUE_API)
all_lights = list(local_bridge.lights())[:1]

tap_beneden = tap_control(bridge=local_bridge, id=2, lights=all_lights)
tap_beneden.init()
switch = tap_beneden.external_switch()

def bed_time():
    return time(23 if clock.date().weekday() in (4, 5) else 22, 45)

def wake_time():
    return time( 8 if clock.date().weekday() in (5, 6) else  7, 15)

ede = location(lat=52.053055, lon=5.638889)

alarm(
    turn_on_between((switch,), wake_time     , ede.dawn_end),
    turn_on_between((switch,), ede.dusk_begin, bed_time    ),
    )


t_wake = time(7,15)
t_sleep = time(22,15)

bri_phase = phase(t_wake, t_sleep, sinus(charge(BRI_SINUS_CHARGE)), 0, 255)


def adjust_brightness(lights, events):
    while True:
        t, v = events.next()
        print "Next event at:", t
        yield t
        print "     setting bri:", v
        for light in lights:
            light.send(bri=v)

from misc import find_next_change
alarm(adjust_brightness(all_lights + [switch], find_next_change(bri_phase)))

while True:
    sleep(1)
