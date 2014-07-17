#!/usr/bin/env python
from sys import stdout
from time import sleep
from datetime import datetime, time
from misc import autostart, lamp, attenuator
from config import WUNDERGROUND_API_KEY, LOCAL_HUE_API
from extended_cct import extend_cct, MIREK
from sunphase import rise_and_set
from phase import phase, unity as linear
from math import sin, pi, exp

"""
We use MIREK instead of Kelvin as unit for color temperature because:
 - this is the unit used by Hue, and Hue just has so many levels
 - it ranges from 100-1000 in 900 steps instead of 9000 steps in Kelvin.
 - it is linear instead of exponential, so color changes more linear
"""

# http://www.apogeephoto.com/july2004/jaltengarten7_2004.shtml
CCT_SUN_RISE = MIREK/2000
CCT_SUN_RISE_PLUS_1 = MIREK/3500
CCT_EARLY_MORNING_LATE_AFTERNOON = MIREK/4300
CCT_AVG_SUMMER_SUNLIGHT = MIREK/5400
CCT_OVERCAST_SKY = MIREK/6000
# my own
CCT_RED_SUN = MIREK/1000
CCT_DEEP_NIGHT = MIREK/10000

@autostart
def sinus(next=linear()):
    x = 0.
    while True:
        x = yield next.send(sin(x * pi))

@autostart
def constant(v):
    while True:
        yield v

@autostart
def exponent(p):
    v = 0.
    c = 1. - exp(-p)
    while True:
        v = yield (1. - exp(-p * v)) / c

def get_ct_phase(sun, t_wake, t_sleep, t_now):
    t_rise, t_set = sun.next()
    t_day_begin, t_day_end = max(t_rise, t_wake), min(t_set, t_sleep)
    t_night_begin, t_night_end = max(t_set, t_sleep), min(t_rise, t_wake)

    if t_day_begin <= t_now < t_day_end:
        print " * day * "
        return phase(t_day_begin, t_day_end, sinus(), CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    elif t_night_end <= t_now < t_day_begin:
        # what if this phase is very short, say a few minutes?
        print " * early morning * "
        return phase(t_night_end, t_day_begin, linear(), CCT_RED_SUN, CCT_SUN_RISE)
    elif t_day_end <= t_now < t_night_begin:
        # what if this phase is very short, say a few minutes?
        print " * late evening * "
        return phase(t_day_end, t_night_begin, linear(), CCT_SUN_RISE, CCT_RED_SUN)
    elif t_night_begin <= t_now < time.max or time.min <= t_now < t_night_end:
        print " * night * "
        return phase(t_night_begin, t_night_end, sinus(), CCT_RED_SUN, CCT_DEEP_NIGHT)
    else:
        raise Exception("Cannot match cycle: %s" % t_now)

def loop(light):
    last_bri = last_ct = 0
    sun = rise_and_set(52.053055, 5.638889, -6.0)
    while True:
        t_now = datetime.now().time()
        t_wake, t_sleep = time(7,15), time(22,15)
        ct_phase = get_ct_phase(sun, t_wake, t_sleep, t_now)

        if t_wake < t_now < t_sleep:
            bri_cycle = phase(t_wake, t_sleep, sinus(exponent(3.)), 0, 255) # plus exp (refactor)
        else:
            bri_cycle = constant(0)

        for color_temp in ct_phase:
            brightness = bri_cycle.next()
            if color_temp != last_ct or brightness != last_bri:
                last_bri = brightness
                last_ct = color_temp
                print "%s; %dK; %.1f%%" % (datetime.now().strftime("%a %H:%M:%S"), MIREK/color_temp, brightness/2.55)
            light.send(dict(ct=color_temp, bri=brightness, on=True))
            stdout.flush()
            sleep(1.0)
        sleep(1.0)


if __name__ == "__main__":
    group1 = lamp(LOCAL_HUE_API + "groups/0/action")
    light1 = extend_cct(attenuator(group1))
    #lamp1 = lamp(LOCAL_HUE_API + "lights/1/state")
    #light1 = extend_cct(lamp1)
    #weather1 = weather("http://api.wunderground.com/api/%s/conditions/q/pws:IUTRECHT57.json" % WUNDERGROUND_API_KEY)
    loop(light1)

