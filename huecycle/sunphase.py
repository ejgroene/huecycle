#!/usr/bin/env python
# -*- coding: utf-8 -*-
from misc import autostart
from clock import clock
from datetime import datetime, time
from ephem import Observer, Sun, localtime
from phase import phase, sinus, charge, linear

@autostart
def rise_and_set(lat, lon, horizon=0):
    sun = Sun()
    date = None
    while True:
        loc = Observer()
        loc.horizon = str(horizon)
        loc.lat = str(lat)
        loc.lon = str(lon)
        loc.date = clock.now()
        #if date:
        #    loc.date = date
        #loc.date = loc.date.datetime().date() # strip time
        t_rise = loc.next_rising(sun)
        t_set = loc.next_setting(sun)
        #date = yield localtime(t_rise), localtime(t_set)
        yield localtime(t_rise), localtime(t_set)

from prototype import object

@object
def location():
    twilight_angle = 6.0 # civil twilight
    def dawn_and_dusk(self):
        if not hasattr(self, '_dawn_and_dusk'):
            self._dawn_and_dusk = rise_and_set(self.lat, self.lon, -self.twilight_angle)
        return self._dawn_and_dusk
    def twilight_zones(self):
        if not hasattr(self, '_twilight_zones'):
            self._twilight_zones = rise_and_set(self.lat, self.lon, self.twilight_angle)
        return self._twilight_zones
    def dawn_begin(self):
        if not hasattr(self, '_begin_dawns'):
            self._begin_dawns = (t_dawn for t_dawn, _ in self.dawn_and_dusk())
        return next(self._begin_dawns)
    def dawn_end(self):
        if not hasattr(self, '_end_dawns'):
            self._end_dawns = (t_dawn for t_dawn, _ in self.twilight_zones())
        return next(self._end_dawns)
    def dusk_begin(self):
        if not hasattr(self, '_begin_dusks'):
            self._begin_dusks = (t_dusk for _, t_dusk in self.twilight_zones())
        return next(self._begin_dusks)
    def dusk_end(self):
        if not hasattr(self, '_end_dusks'):
            self._end_dusks = (t_dusk for _, t_dusk in self.dawn_and_dusk())
        return next(self._end_dusks)
    def twilights(self, time=None):
        t_dawn_begin, t_dusk_end = self.dawn_and_dusk().send(time)
        t_dawn_end, t_dusk_begin = self.twilight_zones().send(time)
        return t_dawn_begin, t_dawn_end, t_dusk_begin, t_dusk_end
    @autostart
    def ct_cycle(self, t_wake, t_sleep):
        t = yield
        while True:
            t_dawn_begin, _, _, t_dusk_end = self.twilights()
            ct_phase = get_ct_phase(t_wake(), t_sleep(), t_dawn_begin.time(), t_dusk_end.time(), t)
            try:
                while True:
                    t = yield round(ct_phase.send(t))
            except StopIteration:
                pass
    return locals()

from autotest import autotest

@autotest
def Twilights():
    ede = location(lat=52, lon=5.6)
    clock.set(datetime(2014,6,26,  12,00,00))
    t_dawn_begin, t_dawn_end, t_dusk_begin, t_dusk_end = ede.twilights(None)
    print(t_dawn_begin, t_dawn_end, t_dusk_begin, t_dusk_end)
    # 21 june:  04:24  06:09  21:09  22:54
    # 21 dec:   07:59  09:42  15:29  17:11
    assert datetime(2014,6,27,  4,24) < t_dawn_begin < datetime(2014,6,27,  8,00), t_dawn_begin
    assert datetime(2014,6,27,  6, 9) < t_dawn_end   < datetime(2014,6,27,  9,43)
    assert datetime(2014,6,26, 15,29) < t_dusk_begin < datetime(2014,6,26, 21,10), t_dusk_begin
    assert datetime(2014,6,26, 17,11) < t_dusk_end   < datetime(2014,6,26, 22,55)

@autotest
def RiseAndSet():
    sun = rise_and_set(52., 5.6)
    clock.set(datetime(2014,6,20, 12,00))
    t_rise, t_set = next(sun)
    assert type(t_rise) == datetime, type(t_rise)
    assert type(t_set) == datetime, type(t_set)
    assert t_rise.replace(microsecond=0) == datetime(2014,6,21,  5,16,55), t_rise
    assert  t_set.replace(microsecond=0) == datetime(2014,6,20, 22,0o1,34), t_set
    clock.set(datetime(2014,6,21, 12,00))
    t_rise, t_set = next(sun) # make sure it finds next, not latest
    assert t_rise.replace(microsecond=0) == datetime(2014,6,22,  5, 17, 9), t_rise
    assert  t_set.replace(microsecond=0) == datetime(2014,6,21, 22,0o1,47), t_set
    clock.set(datetime(2014, 6, 21, 23,00))
    t_rise, t_set = next(sun) # make sure it finds next, not latest
    assert t_rise.replace(microsecond=0) == datetime(2014,6,22,  5, 17, 9), t_rise
    assert  t_set.replace(microsecond=0) == datetime(2014,6,22, 22,0o1,57), t_set

@autotest
def DawnsAndDusks():
    ede = location(lat=52, lon=5.6)
    assert ede.lat == 52
    clock.set(datetime(2014,6,20, 12,00))
    dawn_begin = ede.dawn_begin()
    assert datetime(2014,6,21, 4,24) < dawn_begin < datetime(2014,6,21, 8,00), dawn_begin
    dawn_end = ede.dawn_end()
    assert dawn_end > dawn_begin
    assert datetime(2014,6,21, 6,9) < dawn_end < datetime(2014,6,21, 9,43), dawn_end
    dusk_begin = ede.dusk_begin()
    assert datetime(2014,6,20, 16,00) < dusk_begin < datetime(2014,6,20, 22,00), dusk_begin
    dusk_end = ede.dusk_end()
    assert dusk_end > dusk_begin
    assert datetime(2014,6,20, 17,00) < dusk_end < datetime(2014,6,20, 23,59), dusk_end

"""
We use MIREK instead of Kelvin as unit for color temperature because:
 - this is the unit used by Hue, and Hue just has so many levels
 - it ranges from 100-1000 in 900 steps instead of 9000 steps in Kelvin.
 - it is linear instead of exponential, so color changes more linear
"""

# http://www.apogeephoto.com/july2004/jaltengarten7_2004.shtml
MIREK = 1000000
CCT_SUN_RISE = CCT_SUN_SET = MIREK/2000
CCT_SUN_RISE_PLUS_1 = MIREK/3500
CCT_EARLY_MORNING_LATE_AFTERNOON = MIREK/4300
CCT_AVG_SUMMER_SUNLIGHT = MIREK/5400
CCT_OVERCAST_SKY = MIREK/6000
# my own
CCT_RED_SUN = MIREK/1000
CCT_DEEP_NIGHT = MIREK/10000

def get_ct_phase(t_wake, t_sleep, t_rise, t_set, t):
    if isinstance(t, datetime): t = t.time()
    t_dawn_end = min(t_wake, t_rise)
    t_dusk_begin = max(t_sleep, t_set)
    t_dawn_begin = t_dawn_end.replace(hour=t_dawn_end.hour - 1)
    t_dusk_end = t_dusk_begin.replace(hour=t_dusk_begin.hour + 1) #TODO use datetime for proper rollover
    if t_rise <= t < t_set:
        return phase(t_rise, t_set, sinus(charge(2.)), CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    if t_wake <= t < t_rise:
        return phase(t_wake, t_rise, linear(), CCT_SUN_RISE, CCT_SUN_RISE)
    if t_set <= t < t_sleep:
        return phase(t_set, t_sleep, linear(), CCT_SUN_SET, CCT_SUN_SET)
    if t_dawn_begin <= t < t_dawn_end:
        return phase(t_dawn_begin, t_dawn_end, linear(), CCT_RED_SUN, CCT_SUN_RISE)
    if t_dusk_begin <= t < t_dusk_end:
        return phase(t_dusk_begin, t_dusk_end, linear(), CCT_SUN_SET, CCT_RED_SUN)
    if t_dusk_end <= t < time.max or time.min <= t < t_dawn_begin:
        return phase(t_dusk_end, t_dawn_begin, sinus(), CCT_RED_SUN, CCT_DEEP_NIGHT)
    raise Exception("Cannot match cycle: %s" % t)

def summer_phase(t):
    return get_ct_phase(time(7), time(21), time(6), time(22), t)

@autotest
def summer_day():
    ct = summer_phase(time(0o6,00)).send(time(6,00))
    assert ct == CCT_SUN_RISE, ct
    ct = summer_phase(time(0o6,0o1)).send(time(6,0o1))
    assert ct == 498, ct
    ct = summer_phase(time(21,59)).send(time(21,59))
    assert ct == 498, ct

@autotest
def summer_morning_twilight():
    ct = summer_phase(time(0o5,00)).send(time(5,00))
    assert ct == 1000, ct
    ct = summer_phase(time(0o5,0o1)).send(time(5,0o1))
    assert ct == 992, ct
    ct = summer_phase(time(0o5,59)).send(time(5,59))
    assert ct == 508, ct

@autotest
def summer_evening_twilight():
    ct = summer_phase(time(22,00)).send(time(22,00))
    assert ct == 500, ct
    ct = summer_phase(time(22,0o1)).send(time(22,0o1))
    assert ct == 508, ct
    ct = summer_phase(time(22,59)).send(time(22,59))
    assert ct == 992, ct
  
@autotest
def summer_night():
    ct = summer_phase(time(23,00)).send(time(23,00))
    assert ct == 1000, ct
    ct = summer_phase(time(23,59)).send(time(23,59))
    assert ct == 557, ct
    ct = summer_phase(time(00,00)).send(time(00,00))
    assert ct == 550, ct
    ct = summer_phase(time(00,0o1)).send(time(00,0o1))
    assert ct == 543, ct
    ct = summer_phase(time(0o2,00)).send(time(0o2,00))
    assert ct == 100, ct
    ct = summer_phase(time(0o4,59)).send(time(0o4,59))
    assert ct == 992, ct

def winter_phase(t):
    return get_ct_phase(time(7), time(21), time(8), time(19), t)

@autotest
def winter_day():
    ct = winter_phase(time( 8,00)).send(time( 8,00))
    assert ct == 500, ct
    ct = winter_phase(time( 8,0o1)).send(time( 8,0o1))
    assert ct == 497, ct
    ct = winter_phase(time(18,59)).send(time(18,59))
    assert ct == 497, ct
   
@autotest
def winter_morning_twilight_and_snooze():
    ct = winter_phase(time(0o6,00)).send(time(6,00))
    assert ct == 1000, ct
    ct = winter_phase(time(0o6,0o1)).send(time(6,0o1))
    assert ct ==  992, ct
    ct = winter_phase(time(0o6,59)).send(time(6,59))
    assert ct ==  508, ct
    ct = winter_phase(time(0o7,00)).send(time(7,00))
    assert ct ==  500, ct
    ct = winter_phase(time(0o7,30)).send(time(7,30))
    assert ct ==  500, ct
    ct = winter_phase(time(0o7,59)).send(time(7,59))
    assert ct ==  500, ct

@autotest
def winter_evening_snooze_and_twilight():
    ct = winter_phase(time(19,00)).send(time(19,00))
    assert ct ==  500, ct
    ct = winter_phase(time(20,00)).send(time(20,00))
    assert ct ==  500, ct
    ct = winter_phase(time(20,59)).send(time(20,59))
    assert ct ==  500, ct
    ct = winter_phase(time(21,00)).send(time(21,00))
    assert ct ==  500, ct
    ct = winter_phase(time(21,0o1)).send(time(21,0o1))
    assert ct ==  508, ct
    ct = winter_phase(time(21,59)).send(time(21,59))
    assert ct ==  992, ct

@autotest
def winter_night():
    ct = winter_phase(time(22,00)).send(time(22,00))
    assert ct == 1000, ct
    ct = winter_phase(time(22,0o1)).send(time(22,0o1))
    assert ct ==  994, ct
    ct = winter_phase(time(23,59)).send(time(23,59))
    assert ct ==  368, ct
    ct = winter_phase(time(00,00)).send(time(00,00))
    assert ct ==  364, ct
    ct = winter_phase(time(00,0o1)).send(time(00,0o1))
    assert ct ==  359, ct
    ct = winter_phase(time(0o2,00)).send(time(0o2,00))
    assert ct ==  100, ct
    ct = winter_phase(time(0o5,59)).send(time(0o5,59))
    assert ct ==  994, ct

@autotest
def YearRound():
    ede = location(lat=52, lon=5.6)
    ctc = ede.ct_cycle(lambda: time(7), lambda: time(22))
    def assert_ct(Y, M, D, h, m, ct_soll):
        ct = ctc.send(time(h,m)) # you can send the current time...
        assert ct == round(MIREK/ct_soll), (ct, round(MIREK/ct_soll))
        clock.set(datetime(Y, M, D, h, m)) # or set the global clock.
        ct = next(ctc)
        assert ct == round(MIREK/ct_soll), (ct, round(MIREK/ct_soll))
    assert_ct(2000,6,21, 14,00, 5405)
    assert_ct(2000,6,21, 15,00, 5319)
    assert_ct(2000,6,21, 16,00, 5160)
    assert_ct(2000,6,21, 17,00, 4926)
    assert_ct(2000,6,21, 18,00, 4566)
    assert_ct(2000,6,21, 19,00, 4132)
    assert_ct(2000,6,21, 20,00, 3610)
    assert_ct(2000,6,21, 21,00, 3039)
    assert_ct(2000,6,21, 22,00, 2475)
    assert_ct(2000,6,21, 23,00, 1831)

    assert_ct(2000,6,22, 00,0o1, 1096)
    assert_ct(2000,6,22, 0o1,00, 3952)
    assert_ct(2000,6,22, 0o2,00, 7042)
    assert_ct(2000,6,22, 0o2,10, 5235)
    assert_ct(2000,6,22, 0o2,20, 3861)
    assert_ct(2000,6,22, 0o2,30, 2915)
    assert_ct(2000,6,22, 0o3,00, 1481)
    assert_ct(2000,6,22, 0o4,00, 1410)
    assert_ct(2000,6,22, 0o5,00, 2298)
    assert_ct(2000,6,22, 0o6,00, 2857)
    assert_ct(2000,6,22, 0o7,00, 3426)
    assert_ct(2000,6,22,  8,00, 3968)
    assert_ct(2000,6,22,  9,00, 4444)
    assert_ct(2000,6,22, 10,00, 4810)
    assert_ct(2000,6,22, 11,00, 5102)
    assert_ct(2000,6,22, 12,00, 5291)
    assert_ct(2000,12,21, 14,00, 5405)
    assert_ct(2000,12,21, 15,00, 5319)
    assert_ct(2000,12,21, 16,00, 5181)
    assert_ct(2000,12,21, 17,00, 4926)
    assert_ct(2000,12,21, 18,00, 4566)
    assert_ct(2000,12,21, 19,00, 4132)
    assert_ct(2000,12,21, 20,00, 3610)
    assert_ct(2000,12,21, 21,00, 3048)
    assert_ct(2000,12,21, 22,00, 2475)
    assert_ct(2000,12,21, 23,00, 1000)
    assert_ct(2000,12,22, 00,0o1, 1658)
    assert_ct(2000,12,22, 0o1,00, 3378)
    assert_ct(2000,12,22, 0o2,00, 8130)
    assert_ct(2000,12,22, 0o2,10, 9090)
    assert_ct(2000,12,22, 0o2,20, 9708)
    assert_ct(2000,12,22, 0o2,30, 10000)
    assert_ct(2000,12,22, 0o3,00, 8130)
    assert_ct(2000,12,22, 0o4,00, 3378)
    assert_ct(2000,12,22, 0o5,00, 1639)
    assert_ct(2000,12,22, 0o6,00, 1000)
    assert_ct(2000,12,22, 0o7,00, 2000)
    assert_ct(2000,12,22,  8,00, 2000)
    assert_ct(2000,12,22,  9,00, 3095)
    assert_ct(2000,12,22, 10,00, 4174)
    assert_ct(2000,12,22, 11,00, 4950)
    assert_ct(2000,12,22, 12,00, 5347)

