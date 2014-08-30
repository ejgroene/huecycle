#!/usr/bin/env python
from sys import stdout
from time import sleep
from datetime import datetime, time, timedelta
from misc import autostart, lamp, attenuator, hours
from config import LOCAL_HUE_API
from extended_cct import extend_cct, MIREK
from sunphase import rise_and_set
from phase import phase, linear, sinus, charge, constant
from itertools import izip

"""
We use MIREK instead of Kelvin as unit for color temperature because:
 - this is the unit used by Hue, and Hue just has so many levels
 - it ranges from 100-1000 in 900 steps instead of 9000 steps in Kelvin.
 - it is linear instead of exponential, so color changes more linear
"""

# http://www.apogeephoto.com/july2004/jaltengarten7_2004.shtml
CCT_SUN_RISE = CTT_SUN_SET = MIREK/2000
CCT_SUN_RISE_PLUS_1 = MIREK/3500
CCT_EARLY_MORNING_LATE_AFTERNOON = MIREK/4300
CCT_AVG_SUMMER_SUNLIGHT = MIREK/5400
CCT_OVERCAST_SKY = MIREK/6000
# my own
CCT_RED_SUN = MIREK/1000
CCT_DEEP_NIGHT = MIREK/10000

def get_ct_phase(t_wake, t_sleep, t_rise, t_set, t):
    t_dawn_end = min(t_wake, t_rise)
    t_dusk_begin = max(t_sleep, t_set)
    t_dawn_begin = t_dawn_end.replace(hour=t_dawn_end.hour - 1)
    t_dusk_end = t_dusk_begin.replace(hour=t_dusk_begin.hour + 1)
    if t_rise <= t < t_set:
        print " * Just follow the sun's color."
        return phase(t_rise, t_set, sinus(charge(2.)), CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    if t_wake <= t < t_rise or t_set <= t < t_sleep:
        print " * Awake but no sun."
        return constant(CTT_SUN_SET)
    if t_dawn_begin <= t < t_dawn_end:
        print " * Morning twilight."
        return phase(t_dawn_begin, t_dawn_end, linear(), CCT_RED_SUN, CCT_SUN_RISE)
    if t_dusk_begin <= t < t_dusk_end:
        print " * Evening twilight."
        return phase(t_dusk_begin, t_dusk_end, linear(), CCT_SUN_SET, CCT_RED_SUN)
    if t_dusk_end <= t < time.max or time.min <= t < t_dawn_begin:
        print " * Night."
        return phase(t_dusk_end, t_dawn_begin, sinus(), CCT_RED_SUN, CCT_DEEP_NIGHT)
    raise Exception("Cannot match cycle: %s" % t)


def loop(light):
    last_bri = last_ct = 0
    sun = rise_and_set(52.053055, 5.638889, -6.0)
    t_wake = time(7,15)
    t_sleep = time(22,15)
    while True:
        t_rise, t_set = sun.next()
        ct_phase = get_ct_phase(t_wake, t_sleep, t_rise, t_set, datetime.now().time())
        bri_phase = phase(t_wake, t_sleep, sinus(charge(3.)), 0, 255)
        for color_temp, brightness in izip(ct_phase, bri_phase):
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

