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

clock.set()

ede = location(lat=52.053055, lon=5.638889)

def t_lights_off():
    while True:
        yield time(23 if clock.date().weekday() in (4, 5) else 22, 45)

lights = lights_controller(baseurl=LOCAL_HUE_API)

all_lights = list(lights.lights())
alarm(
    turn_on_between(all_lights, lambda: time(7,00), ede.next_dawn_end),
    turn_on_between(all_lights, ede.next_dusk, t_lights_off().next),
    )


t_wake = time(7,15)
t_sleep = time(22,45)

bri_phase = phase(t_wake, t_sleep, sinus(charge(BRI_SINUS_CHARGE)), 0, 255)
def filter_new_values(g):
    t = datetime.now()
    last = g.next()
    yield t, last
    while True:
        t = datetime.now()
        next = g.send(t)
        while next == last:
            t = t + timedelta(seconds=1)
            next = g.send(t)
        yield t, next
        last = next

def adjust_brightness(light, events):
    while True:
        t, v = events.next()
        print "Next event at:", t
        yield t
        print "     setting bri:", v
        light.set_state(bri=v)

#alarm(adjust_brightness(all_lights[0], filter_new_values(bri_phase)))

f = filter_new_values(bri_phase)
while True:
    sleep(1)
