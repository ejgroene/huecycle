#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sunphase import location
from datetime import time
from config import LOCAL_HUE_API
from controllers import turn_on_between
from alarm import alarm
from config import BRI_SINUS_CHARGE
from phase import sinus, charge
from brightness import brightness_cycle
from datetime import datetime, timedelta
from time import sleep
from clock import clock

from bridge import bridge
from tap import tap_control
from misc import find_next_change
from random import randint
from rules import delete_all_rules
from sensors import delete_all_sensors

clock.set()
delete_all_rules(LOCAL_HUE_API)
delete_all_sensors(LOCAL_HUE_API)

local_bridge = bridge(baseurl=LOCAL_HUE_API)
local_bridge.delete_groups()

s1 = local_bridge.sensor("keuken")
s2 = local_bridge.sensor("woonkamer")

tap_keuken = tap_control(bridge=local_bridge, id=s1.id, lights=tuple(local_bridge.lights("keuken")))
tap_keuken.init()
tap_woonkamer = tap_control(bridge=local_bridge, id=s2.id, lights=tuple(local_bridge.lights("woonkamer")))
tap_woonkamer.init()

light_studeer = (local_bridge.lights("studeer")).next()
lights_all = (light_studeer, tap_keuken, tap_woonkamer)

def bed_time():
    t = clock.nexttime(time(22,30))
    if t.weekday() in (4, 5):
        t+= timedelta(minutes=29) #FIXME later than 22h59 won't work
    return t.time()

def wake_time():
    t = clock.nexttime(time(7,15))
    if t.weekday() in (5, 6):
        t+= timedelta(hours=1)
    return t.time()

ede = location(lat=52.053055, lon=5.638889)

bri_cycle = find_next_change(brightness_cycle(wake_time, bed_time, sinus(charge(BRI_SINUS_CHARGE))))
ct_cycle = find_next_change(ede.ct_cycle(wake_time, bed_time))

def process_events(lights, events, attr):
    while True:
        t, v = events.next()
        print "Next %s event at:" % attr, t
        yield t
        print "     setting %s:" % attr, v
        for light in lights:    
            light.send(**{attr:v})

alarm(
    turn_on_between((light_studeer, tap_keuken), wake_time, ede.dawn_end), #TODO remove woonkamer
    turn_on_between(lights_all, ede.dusk_begin, bed_time),
    process_events(lights_all, bri_cycle, 'bri'),
    process_events(lights_all, ct_cycle, 'ct')
    )

while True:
    sleep(10)
