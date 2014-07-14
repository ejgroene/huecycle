from misc import autotest, autostart
from datetime import datetime, date, time
from ephem import Observer, Sun, localtime

@autostart
def rise_and_set(lat, lon, horizon=0):
    sun = Sun()
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
