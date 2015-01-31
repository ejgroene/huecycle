#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sunphase import location
from datetime import time
from config import LOCAL_HUE_API
from lights import lights_controller
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

ede = location(lat=52.053055, lon=5.638889)

def bed_time():
    return time(23 if clock.date().weekday() in (4, 5) else 22, 45)

def wake_time():
    return time( 8 if clock.date().weekday() in (5, 6) else  7, 15)


lights = lights_controller(baseurl=LOCAL_HUE_API)

all_lights = list(lights.lights())
alarm(
    turn_on_between(all_lights, wake_time     , ede.dawn_end),
    turn_on_between(all_lights, ede.dusk_begin, bed_time    ),
    )


local_bridge = bridge(baseurl=LOCAL_HUE_API)

tap_beneden = tap_control(bridge=local_bridge, id=2, lights=(1, 2, 3, 4, 5) )
tap_beneden.init()

t_wake = time(7,15)
t_sleep = time(22,15)

bri_phase = phase(t_wake, t_sleep, sinus(charge(BRI_SINUS_CHARGE)), 0, 255)


def adjust_brightness(light, events):
    while True:
        t, v = events.next()
        print "Next event at:", t
        yield t
        print "     setting bri:", v
        light.set_state(bri=v)

#alarm(adjust_brightness(all_lights[0], filter_new_values(bri_phase)))
#f = filter_new_values(bri_phase)

while True:
    sleep(1)
