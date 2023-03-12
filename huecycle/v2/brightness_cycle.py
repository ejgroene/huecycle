import autotest
test = autotest.get_tester(__name__)

from datetime import time, datetime, timedelta
from zoneinfo import ZoneInfo
from ephem import Observer, Sun, localtime, to_timezone
from math import sin, pi


utc = ZoneInfo('UTC')
day = timedelta(hours=24)


def ephem_to_datetime(e):
    return to_timezone(e, utc).replace(second=0, microsecond=0)


class cct_cycle:

    def __init__(self, lat, lon, t_wake, t_sleep, cct_min, cct_sun, cct_moon, br_dim, br_max):
        assert isinstance(lat, str), lat
        assert isinstance(lon, str), lon
        assert t_wake.second == t_sleep.second == t_wake.microsecond == t_wake.microsecond == 0
        assert 1000 <= cct_min  <= 20000, cct_min
        assert 3000 <= cct_sun  <= 10000, cct_sun
        assert 3000 <= cct_moon <= 20000, cct_moon
        assert cct_min < cct_sun < cct_moon
        assert      1 <= br_dim <  100, br_dim
        assert br_dim  < br_max <= 100, br_max
        self.t_wake   = t_wake     # time you wake up
        self.t_sleep  = t_sleep    # time you go to sleep
        self.cct_min  = cct_min    # minimum CCT at dusk and dawn
        self.cct_sun  = cct_sun    # maximum CCT during day
        self.cct_moon = cct_moon   # maximum CCT during night
        self.br_dim   = br_dim     # brightness night light
        self.br_max   = br_max     # full brightness
        self.sun      = Sun()
        self.obs      = Observer()
        self.obs.lon  = lon        # longitude in "52:01.224" format
        self.obs.lat  = lat        # latitude in "5:41.065" format
        self.obs.elevation = 6.0   # twilight angle (civil = 6)
   

    def phase(self, t0, t1, t2):
        assert t0 <= t1 <= t2
        return pi * (t1 - t0) / (t2 - t0) 


    def value(self, t_given=None):
        """
            ----------------- timeline (| =  midnight) -----------------------
              winter:        | wakeup  sunrise  noon  sunset  sleep |
              summer:        | sunrise  wakeup  noon  sleep  sunset |
                                     \ /                    \ /
             general:  end_0 |      start       noon        end     |  start_1

            1. between wakeup - sunrise and between sunset - sleep, CCT is cct_min
            2. between start - end, CCT follows sinusoidal curve peaking at cct_sun,
            3. between end - start, CTT follows sinusoidal curve peaking at cct_moon,
            4. brightness is a flat line, at br_dim, between sleep and wake,
            5. brightness is a half sinusoidal between wake and sleep, peaking at br_max.
            NB: to be able to test exact boundaries we round all times to minutes 
        """
        t_now     = t_given.astimezone(utc) if t_given else datetime.now().astimezone(utc)
        today     = t_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(utc)
        t_rise    = ephem_to_datetime(self.obs.next_rising (self.sun, start=today))
        t_noon    = ephem_to_datetime(self.obs.next_transit(self.sun, start=today))
        t_set     = ephem_to_datetime(self.obs.next_setting(self.sun, start=today))
        t_wake    = datetime.combine(today, self.t_wake ).astimezone(utc)
        t_sleep   = datetime.combine(today, self.t_sleep).astimezone(utc)
        t_start   = min(t_wake, t_rise)
        t_end     = max(t_set, t_sleep)
        t_start_1 = min(t_wake + day, t_rise + day)
        t_end_0   = max(t_set - day, t_sleep - day)

        assert t_wake < t_sleep
        assert t_wake < t_noon
        assert t_sleep > t_noon
        assert t_rise < t_noon
        assert t_set > t_noon

        if t_wake < t_now < t_sleep:
            br = int(sin(self.phase(t_wake, t_now, t_sleep)) * (self.br_max - self.br_dim) + self.br_dim)
        else:
            br = self.br_dim

        cct_max = self.cct_sun

        # winter, when sunrise is later than start time
        if t_wake <= t_now < t_rise:
            f = 0
        # winter, when sunset comes before end time
        elif t_set < t_now <= t_sleep:
            f = 0

        # rising value until noon
        elif t_rise <= t_now < t_noon:
            f = 1/2 * self.phase(t_rise, t_now, t_noon)
        # lowering value after noon
        elif t_noon <= t_now <= t_set:
            f = 1/2 * pi + 1/2 * self.phase(t_noon, t_now, t_set)

        # late night, after both end and set
        elif t_end < t_now < t_start_1:
            f = self.phase(t_end, t_now, t_start_1)
            cct_max = self.cct_moon
        # early night, before both start and rise
        elif t_end_0 < t_now < t_start:
            f = self.phase(t_end_0, t_now, t_start)
            cct_max = self.cct_moon

        else:
            print(t_now)
            return

        return int(sin(f) * (cct_max - self.cct_min) + self.cct_min), br
    



@test
def create_cycle():
    ams = ZoneInfo('Europe/Amsterdam')
    c = cct_cycle(
        lat      = "52:01.224",
        lon      =  "5:41.065",
        t_wake   = time(hour= 8, tzinfo=ams),
        t_sleep  = time(hour=22, tzinfo=ams),
        cct_min  =  2500,
        cct_sun  =  6000,
        cct_moon = 10000,
        br_dim   =     2,
        br_max   =    99)

    test.eq([(8567,  2), (9632,  2), (10000, 2), (9632,  2), (8567,  2), (6908,  2), (4817, 2), # night
             (2500,  2), (2850, 23), (4182, 44), (5246, 62), (5875, 77), (5969, 89),            # morning
             (5515, 96), (4587, 99), (3330, 96), (2500, 89),                                    # afternoon
             (2500, 77), (2500, 62), (2500, 44), (2500, 23), (2500, 2),                         # evening
             (4817,  2), (6908,  2),                                                            # late night
        ],
        [c.value(datetime(2023, 1, 1, hour=h, tzinfo=utc)) for h in range(0, 24)],
        diff=test.diff) 

    test.eq([(8181,  2), (9711,  2), (9909, 2), (8737, 2), (6412, 2), (3364, 2), (2979, 2),       # night
             (3616,  2), (4215,  2),                                                              # still sleeping
             (4753, 23), (5212, 44), (5577, 62), (5834, 77), (5974, 89), (5992, 96),              # 8 - 14h
             (5888, 99), (5664, 96), (5330, 89), (4896, 77), (4377, 62), (3793, 44), (3164, 23),  # 15 - 21h
             (2510,  2), (5599,  2),                                                              # 22 - 23h
        ],
        [c.value(datetime(2023, 6, 21, hour=h)) for h in range(0, 24)],
        diff=test.diff) 

    # in summer, lowest CCT and brightness should be precisely on sun rise or set
    test.eq((2500, 2), c.value(datetime(2023, 6, 21, hour= 5, minute=16)))
    test.eq((2500, 2), c.value(datetime(2023, 6, 21, hour=22, minute= 1)))

    # in summer, higest CCT should be at sun transit and middle bwteen set and rise
    test.eq((6000, 94), c.value(datetime(2023, 6, 21, hour=13, minute=39)))
    test.eq((9999,  2), c.value(datetime(2023, 6, 22, hour= 1, minute=39)))

    # in winter, lowest CTT should be between wake and rise
    test.eq((2500,  2), c.value(datetime(2023, 12, 21, hour= 8)))
    test.eq((2500, 17), c.value(datetime(2023, 12, 21, hour= 8, minute=42)))
    # and set and sleep
    test.eq((2500, 93), c.value(datetime(2023, 12, 21, hour=16, minute=28)))
    test.eq((2500,  2), c.value(datetime(2023, 12, 21, hour=22)))

    # in winter, higest value should be at sun transit and middle bwteen sleep and wake
    test.eq(( 6000, 85), c.value(datetime(2023, 12, 21, hour=12, minute=35)))
    test.eq((10000,  2), c.value(datetime(2023, 12, 22, hour= 3)))


@test
def real_cycle():
    ams = ZoneInfo('Europe/Amsterdam')
    c = cct_cycle(
        lat      = "52:01.224",
        lon      =  "5:41.065",
        t_wake   = time(hour= 6, tzinfo=ams),
        t_sleep  = time(hour=23, tzinfo=ams),
        cct_min  =  1000,
        cct_sun  =  5000,
        cct_moon = 20000,
        br_dim   =    10,
        br_max   =   100)

    cct, br = c.value()
    test.contains(range(1000, 5001), cct) # it just depends on when you run this test
    test.contains(range(10, 101), br)
