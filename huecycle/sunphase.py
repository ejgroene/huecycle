from misc import autotest, autostart, hours
from datetime import datetime, date, time
from ephem import Observer, Sun, Moon, localtime
from phase import phase, sinus, charge, linear

@autostart
def rise_and_set(lat, lon, horizon=0):
    sun = Sun()
    moon = Moon()
    date = None
    while True:
        loc = Observer()
        loc.horizon = str(horizon)
        loc.lat = str(lat)
        loc.lon = str(lon)
        if date:
            loc.date = date
        loc.date = loc.date.datetime().date() # strip time
        t_rise = loc.next_rising(sun)
        t_set = loc.next_setting(sun)
        date = yield localtime(t_rise).time(), localtime(t_set).time()

@autotest
def testRiseAndSet():
    sun = rise_and_set(52., 5.6)
    t_rise, t_set = sun.next()
    assert type(t_rise) == time, type(t_rise)
    assert type(t_set) == time, type(t_set)
    t_rise, t_set = sun.send(date(2014,6,21))
    assert t_rise == time(5,16,55,000005), t_rise
    assert t_set == time(22,01,47,000005), t_set
    t_rise, t_set = sun.send(datetime(2014,6,21,12,00)) # make sure it finds latest, not next sun rise
    assert t_rise == time(5,16,55,000005), t_rise
    assert t_set == time(22,01,47,000005), t_set


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
    t_dawn_end = min(t_wake, t_rise)
    t_dusk_begin = max(t_sleep, t_set)
    t_dawn_begin = t_dawn_end.replace(hour=t_dawn_end.hour - 1)
    t_dusk_end = t_dusk_begin.replace(hour=t_dusk_begin.hour + 1)
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
    assert false

@autotest
def changes_generator():
    ct_gen = ct_events(time(7), time(21), time(6), time(22))
    assert ct_gen

@autotest
def summer_day():
    ct = summer_phase(time(06,00)).send(time(6,00))
    assert ct == CCT_SUN_RISE, ct
    ct = summer_phase(time(06,01)).send(time(6,01))
    assert ct == 498, ct
    ct = summer_phase(time(21,59)).send(time(21,59))
    assert ct == 498, ct

@autotest
def summer_morning_twilight():
    ct = summer_phase(time(05,00)).send(time(5,00))
    assert ct == 1000, ct
    ct = summer_phase(time(05,01)).send(time(5,01))
    assert ct == 992, ct
    ct = summer_phase(time(05,59)).send(time(5,59))
    assert ct == 508, ct

@autotest
def summer_evening_twilight():
    ct = summer_phase(time(22,00)).send(time(22,00))
    assert ct == 500, ct
    ct = summer_phase(time(22,01)).send(time(22,01))
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
    ct = summer_phase(time(00,01)).send(time(00,01))
    assert ct == 543, ct
    ct = summer_phase(time(02,00)).send(time(02,00))
    assert ct == 100, ct
    ct = summer_phase(time(04,59)).send(time(04,59))
    assert ct == 992, ct

def winter_phase(t):
    return get_ct_phase(time(7), time(21), time(8), time(19), t)

@autotest
def winter_day():
    ct = winter_phase(time( 8,00)).send(time( 8,00))
    assert ct == 500, ct
    ct = winter_phase(time( 8,01)).send(time( 8,01))
    assert ct == 497, ct
    ct = winter_phase(time(18,59)).send(time(18,59))
    assert ct == 497, ct
   
@autotest
def winter_morning_twilight_and_snooze():
    ct = winter_phase(time(06,00)).send(time(6,00))
    assert ct == 1000, ct
    ct = winter_phase(time(06,01)).send(time(6,01))
    assert ct ==  992, ct
    ct = winter_phase(time(06,59)).send(time(6,59))
    assert ct ==  508, ct
    ct = winter_phase(time(07,00)).send(time(7,00))
    assert ct ==  500, ct
    ct = winter_phase(time(07,30)).send(time(7,30))
    assert ct ==  500, ct
    ct = winter_phase(time(07,59)).send(time(7,59))
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
    ct = winter_phase(time(21,01)).send(time(21,01))
    assert ct ==  508, ct
    ct = winter_phase(time(21,59)).send(time(21,59))
    assert ct ==  992, ct

@autotest
def winter_night():
    ct = winter_phase(time(22,00)).send(time(22,00))
    assert ct == 1000, ct
    ct = winter_phase(time(22,01)).send(time(22,01))
    assert ct ==  994, ct
    ct = winter_phase(time(23,59)).send(time(23,59))
    assert ct ==  368, ct
    ct = winter_phase(time(00,00)).send(time(00,00))
    assert ct ==  364, ct
    ct = winter_phase(time(00,01)).send(time(00,01))
    assert ct ==  359, ct
    ct = winter_phase(time(02,00)).send(time(02,00))
    assert ct ==  100, ct
    ct = winter_phase(time(05,59)).send(time(05,59))
    assert ct ==  994, ct

