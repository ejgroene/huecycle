import autotest
test = autotest.get_tester(__name__)

from datetime import time, datetime, timedelta
from zoneinfo import ZoneInfo
from prototype3 import prototype
from ephem import Observer, Sun, localtime, to_timezone
from math import sin, pi

ams = ZoneInfo('Europe/Amsterdam')
utc = ZoneInfo('UTC')
day = timedelta(hours=24)


"""
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
"""


class cct_cycle:
    def __init__(self, lat, lon, t_start, t_end, v_min, v_max):
        self.t_start = t_start
        self.t_end = t_end
        self.v_min = v_min
        self.v_max = v_max
        self.sun = Sun()
        self.obs = Observer()
        self.obs.lon = lon
        self.obs.lat = lat
        self.obs.elevation = 6.0 # civil twilight
    
    def value_at(self, t_given=None):
        t_now = t_given.astimezone(utc) if t_given else datetime.now().astimezone(utc)
        today = t_now.replace(hour=0, minute=0, second=0).astimezone(utc)
        t_rise  = to_timezone(self.obs.next_rising (self.sun, start=today), utc)
        t_noon  = to_timezone(self.obs.next_transit(self.sun, start=today), utc)
        t_set   = to_timezone(self.obs.next_setting(self.sun, start=today), utc)
        t_start = datetime.combine(today, self.t_start).astimezone(utc)
        t_start_1 = t_start + day
        t_end   = datetime.combine(today, self.t_end  ).astimezone(utc)
        t_end_0 = t_end - day

        t_0 = min(t_start, t_rise)
        t_0_1 = min(t_start_1, t_rise + day)
        t_3 = max(t_set, t_end)


        assert t_start < t_end
        assert t_start < t_noon
        assert t_end > t_noon
        assert t_rise < t_noon
        assert t_set > t_noon

        if t_start <= t_now <= t_rise:
            f = 0
        elif t_set <= t_now <= t_end:
            f = 0

        elif t_rise <= t_now <= t_noon:
            f = 1/2 * pi * (t_now - t_rise) / (t_noon - t_rise)
        elif t_noon <= t_now <= t_set:
            f = 1/2 * pi + 1/2 * pi * (t_now - t_noon) / (t_set - t_noon)

        elif t_3 <= t_now <= t_0_1:
            f = pi * (t_now - t_3) / (t_0_1 - t_3)
        elif t_end_0 <= t_now <= t_0:
            f = pi * (t_now - t_end_0) / (t_0 - t_end_0)

        else:
            return
        CCT = sin(f) * (self.v_max - self.v_min) + self.v_min 
        return int(CCT)
    



@test
def create_cycle():
    c = cct_cycle(
        lat = "52:01.224",
        lon =  "5:41.065",
        t_start = time(hour=8, tzinfo=ams),
        t_end = time(hour=22, tzinfo=ams),
        v_min = 2500,
        v_max = 6000)

    test.eq([5331, 5828, 6000, 5828, 5331, 4557, 3581,  # night
             2500, 2848, 4177, 5240, 5872, 5971,        # morging
             5522, 4598, 3342, 2500,                    # afternoon
             2500, 2500, 2500, 2500, 2500,              # evening
             3581, 4557,                                # late night
        ], [c.value_at(datetime(2023, 1, 1, hour=h, tzinfo=utc)) for h in range(0, 24)], diff=test.diff) 

    test.eq([5957, 5411, 4330, 2913, 2974,
             3612, 4212, 4751, 5211, 5576, 5833, 5973, 5992,
             5888, 5665, 5331, 4898, 4381, 3798, 3169, 2517,
             3932, 5141, 5861,
        ], [c.value_at(datetime(2023, 6, 21, hour=h, tzinfo=utc)) for h in range(0, 24)]) 
