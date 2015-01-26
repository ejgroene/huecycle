#!/usr/bin/env python
# -*- coding: utf-8 -*-


from sunphase import location
ede = location(lat=52.053055, lon=5.638889)

from datetime import time
t_wake = time(7,15)
t_sleep = time(22,45)

from config import LOCAL_HUE_API
from lights import lights_controller
lights = lights_controller(baseurl=LOCAL_HUE_API)

from controllers import switch_group_randomly
from alarm import alarm
all_lights = list(lights.lights())
alarm(
    )


from config import BRI_SINUS_CHARGE
from phase import phase, sinus, charge
from datetime import datetime, timedelta
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

from time import sleep
f = filter_new_values(bri_phase)
while True:
    sleep(1)
