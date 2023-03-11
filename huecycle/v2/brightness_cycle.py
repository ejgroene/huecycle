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
    def __init__(self, lat, lon, t_wake, t_sleep, v_min, v_max):
        self.t_wake  = t_wake
        self.t_sleep = t_sleep
        self.v_min   = v_min
        self.v_max   = v_max
        self.sun     = Sun()
        self.obs     = Observer()
        self.obs.lon = lon
        self.obs.lat = lat
        self.obs.elevation = 6.0 # civil twilight
   
    def phase(self, t0, t1, t2):
        return pi * (t1-t0) / (t2-t0) 

    def value_at(self, t_given=None):
        t_now = t_given.astimezone(utc) if t_given else datetime.now().astimezone(utc)
        today = t_now.replace(hour=0, minute=0, second=0).astimezone(utc)
        t_rise  = to_timezone(self.obs.next_rising (self.sun, start=today), utc)
        t_noon  = to_timezone(self.obs.next_transit(self.sun, start=today), utc)
        t_set   = to_timezone(self.obs.next_setting(self.sun, start=today), utc)
        t_wake  = datetime.combine(today, self.t_wake ).astimezone(utc)
        t_sleep = datetime.combine(today, self.t_sleep).astimezone(utc)

        # we need these to have different starting points during winter or summer
        t_start      = min(t_wake, t_rise)     # earliest of given wake and sunrise
        t_end        = max(t_set, t_sleep)     # latest of sunset and given sleep time
        # we need these to get the begin and end of the day right
        t_start_next = min(t_wake + day, t_rise + day)    # idem, for next day    
        t_end_prev   = max(t_set - day, t_sleep - day)    # idem, for previous day

        assert t_wake < t_sleep
        assert t_wake < t_noon
        assert t_sleep > t_noon
        assert t_rise < t_noon
        assert t_set > t_noon

        # brightness is a flat line between t_sleep and t_wake
        # and a half sinus between t_wake and t_sleep
        if t_wake <= t_now <= t_sleep:
            br = int(sin(self.phase(t_wake, t_now, t_sleep)) * 98 + 2)
        else:
            br = 2

        # winter, when sunrise is later than start time
        if t_wake <= t_now <= t_rise:
            f = 0
        # winter, when sunset comes before end time
        elif t_set <= t_now <= t_sleep:
            f = 0

        # rising value until noon
        elif t_rise <= t_now <= t_noon:
            f = 1/2 * self.phase(t_rise, t_now, t_noon)
        # lowering value after noon
        elif t_noon <= t_now <= t_set:
            f = 1/2 * pi + 1/2 * self.phase(t_noon, t_now, t_set)

        # late night, after both end and set
        elif t_end <= t_now <= t_start_next:
            f = self.phase(t_end, t_now, t_start_next)
        # early night, before both start and rise
        elif t_end_prev <= t_now <= t_start:
            f = self.phase(t_end_prev, t_now, t_start)

        else:
            return

        return int(sin(f) * (self.v_max - self.v_min) + self.v_min )
    



@test
def create_cycle():
    c = cct_cycle(
        lat = "52:01.224",
        lon =  "5:41.065",
        t_wake = time(hour=8, tzinfo=ams),
        t_sleep = time(hour=22, tzinfo=ams),
        v_min = 2500,
        v_max = 6000)

    test.eq([5331, 5828, 6000, 5828, 5331, 4557, 3581,  # night
             2500, 2848, 4177, 5240, 5872, 5971,        # morning
             5522, 4598, 3342, 2500,                    # afternoon
             2500, 2500, 2500, 2500, 2500,              # evening
             3581, 4557,                                # late night
        ],
        [c.value_at(datetime(2023, 1, 1, hour=h, tzinfo=utc)) for h in range(0, 24)],
        diff=test.diff) 

    test.eq([5145, 5863, 5959, 5418, 4336, 2915, 2974,        # night
             3612, 4212, 4751, 5211, 5576, 5833, 5973, 5992,  # 7 - 14h
             5888, 5665, 5331, 4898, 4381, 3798, 3169, 2517,  # 15 - 22h
             3932,                                            # 23h
        ],
        [c.value_at(datetime(2023, 6, 21, hour=h)) for h in range(0, 24)],
        diff=test.diff) 

    # in summer, lowest value should be precisely on sun rise or set
    test.eq(2500, c.value_at(datetime(2023, 6, 21, hour= 5, minute=16, second=27)))
    test.eq(2500, c.value_at(datetime(2023, 6, 21, hour=22, minute= 1, second=36)))

    # in summer, higest value should be at sun transit and middle bwteen set and rise
    test.eq(5999, c.value_at(datetime(2023, 6, 21, hour=13, minute=39)))
    test.eq(5999, c.value_at(datetime(2023, 6, 22, hour= 1, minute=39)))

    # in winter, lowest value should be between wake and rise
    test.eq(2500, c.value_at(datetime(2023, 12, 21, hour= 8)))
    test.eq(2500, c.value_at(datetime(2023, 12, 21, hour= 8, minute=42, second=30)))
    # and set and sleep
    test.eq(2500, c.value_at(datetime(2023, 12, 21, hour=16, minute=27, second=51)))
    test.eq(2500, c.value_at(datetime(2023, 12, 21, hour=22)))

    # in winter, higest value should be at sun transit and middle bwteen sleep and wake
    test.eq(5999, c.value_at(datetime(2023, 12, 21, hour=12, minute=35, second=41)))
    test.eq(6000, c.value_at(datetime(2023, 12, 22, hour= 3)))

    # TODO brightness
