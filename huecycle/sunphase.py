from misc import autotest, autostart, interpolate
from datetime import date, datetime
from ephem import Observer, Sun
from math import sin, pi, exp, copysign

@autostart
def sunphase(lat, lon, horizon=0, boost=2.):
    sun = Sun()
    c = 1. - exp(-boost) if boost else None
    T = yield
    while True:
        if T:
            date, now = T
        else:
            now = datetime.utcnow()  #TODO TESTME
            date = now.date()
        loc = Observer()
        loc.horizon = str(horizon)
        loc.lat = str(lat)
        loc.lon = str(lon)
        loc.date = now
        now = loc.date
        loc.date = date
        t_rise = loc.next_rising(sun)
        t_set = loc.next_setting(sun)
        factor = (now + 0. - t_rise + 0.) / (t_set + 0. - t_rise + 0.)
        angle = sin(factor * pi)
        phase = copysign((1. - exp(-boost * abs(angle))) / c if boost else angle, angle)
        T = yield phase

# http://www.apogeephoto.com/july2004/jaltengarten7_2004.shtml
CCT_SUN_RISE = 2000
CCT_SUN_RISE_PLUS_1 = 3500
CCT_EARLY_MORNING_LATE_AFTERNOON = 4300
CCT_AVG_SUMMER_SUNLIGHT = 5400
CCT_OVERCAST_SKY = 6000

@autotest
def testSunPhaseAgainstGivenCTT():
    s = sunphase(52., 5.6)
    p = s.send((date(2014, 6, 21), datetime(2014, 6, 21, 3, 17))) # just dawn (UTC)
    ct =  interpolate(0., 1., p, CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    assert 2000 < ct < 2050, ct
    
    p = s.send((date(2014, 6, 21), datetime(2014, 6, 21, 4, 17))) # sun rise +1h
    ct =  interpolate(0., 1., p, CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    assert 3200 < ct < 3500, ct # fair enough

    p = s.send((date(2014, 6, 21), datetime(2014, 6, 21, 5, 17))) # "early morning" 
    ct =  interpolate(0., 1., p, CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    assert 4000 < ct < 4300, ct # fair enough

    p = s.send((date(2014, 6, 21), datetime(2014, 6, 21, 12))) # noon (UTC)
    ct =  interpolate(0., 1., p, CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    assert 5300 < ct < 5400, ct

    p = s.send((date(2014, 6, 21), datetime(2014, 6, 21, 18))) # "late afternoon" 
    ct =  interpolate(0., 1., p, CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    assert 4000 < ct < 4300, ct # fair enough

    p = s.send((date(2014, 6, 21), datetime(2014, 6, 21, 20))) # just before sunset (UTC)
    ct =  interpolate(0., 1., p, CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT)
    assert 2000 < ct < 2050, ct
