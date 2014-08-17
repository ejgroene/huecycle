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

class Cycle(object):
    def __init__(self, lat, lon, hor, t_wake, t_sleep):
        self.sun = rise_and_set(lat, lon, hor)
        self.t_wake = t_wake
        self.t_sleep = t_sleep

    def calculate(self, t_now):
        self.t_now = t_now
        self.t_rise, self.t_set = self.sun.next()
        self.t_day_begin, self.t_day_end = max(self.t_rise, self.t_wake), min(self.t_set, self.t_sleep)
        self.t_night_begin, self.t_night_end = max(self.t_set, self.t_sleep), min(self.t_rise, self.t_wake)
        if hours(self.t_night_begin) - hours(self.t_day_end) < 1.:
            self.t_night_begin = self.t_day_end.replace(hour=self.t_day_end.hour + 1)
        if hours(self.t_day_begin) - hours(self.t_night_end) < 1.:
            self.t_night_end = self.t_day_begin.replace(hour=self.t_day_begin.hour - 1)

    def ct_phase(self):
        if self.t_day_begin <= self.t_now < self.t_day_end:
            print " * day * ", self.t_day_begin, self.t_day_end
            return phase(self.t_day_begin, self.t_day_end, sinus(charge(2.)), CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
        elif self.t_night_end <= self.t_now < self.t_day_begin:
            print " * morning * ", self.t_night_end, self.t_day_begin
            return phase(self.t_night_end, self.t_day_begin, linear(), CCT_RED_SUN, CCT_SUN_RISE)
        elif self.t_day_end <= self.t_now < self.t_night_begin:
            print " * evening * ", self.t_day_end, self.t_night_begin
            # on 21 dec, t_day_end is 16h29. It will start to become red already! What about it???
            return phase(self.t_day_end, self.t_night_begin, linear(), CCT_SUN_RISE, CCT_RED_SUN)
        elif self.t_night_begin <= self.t_now < time.max or time.min <= self.t_now < self.t_night_end:
            print " * night * ", self.t_night_begin, self.t_night_end
            return phase(self.t_night_begin, self.t_night_end, sinus(), CCT_RED_SUN, CCT_DEEP_NIGHT)
        else:
            raise Exception("Cannot match cycle: %s" % self.t_now)

    def bri_phase(self):
        if self.t_wake < self.t_now < self.t_sleep:
            return phase(self.t_wake, self.t_sleep, sinus(charge(3.)), 0, 255)
        else:
            return constant(0)

def loop(light):
    last_bri = last_ct = 0
    cycle = Cycle(52.053055, 5.638889, -6.0, time(7,15), time(22,15))
    while True:
        cycle.calculate(datetime.now().time())
        ct_phase = cycle.ct_phase()
        bri_phase = cycle.bri_phase()
        for color_temp, brightness in izip(ct_phase, bri_phase):
            if color_temp != last_ct or brightness != last_bri:
                last_bri = brightness
                last_ct = color_temp
                print "%s; %dK; %.1f%%" % (datetime.now().strftime("%a %H:%M:%S"), MIREK/color_temp, brightness/2.55)
            try:
                light.send(dict(ct=color_temp, bri=brightness, on=True))
            except ConnectionError, e:
                print e
                sleep(60)
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

