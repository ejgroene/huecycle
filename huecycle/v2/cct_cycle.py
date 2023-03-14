import autotest
test = autotest.get_tester(__name__)

import asyncio
from datetime import time, datetime, timedelta
from zoneinfo import ZoneInfo
from ephem import Observer, Sun, localtime, to_timezone
from math import sin, pi


MIREK = 10**6

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


    def cct_brightness(self, t_given=None):
        """
            1. The timeline is as follows:

                 winter:         | wakeup  sunrise  noon  sunset  sleep |
                 summer:         | sunrise  wakeup  noon  sleep  sunset |
                                       \ /                    \ /
              cct cycle:  end_0  |    start         noon      end       |  start_1
             brightness:         |          wakeup  noon          sleep |

            2. To be able to test exact boundaries we round all times to minutes.
            3. Brightness cycle is asymmetric: wakeup...noon..............sleep.
            4. Night cycle for CCT is delimited by start and end, depends on season
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

        assert t_end_0  <  t_wake  <  t_noon  <  t_sleep <  t_start_1
        assert t_end_0  <  t_rise  <  t_noon  <  t_set   <  t_start_1
        assert t_end_0  <  t_start <  t_noon  <  t_end   <  t_start_1
        

        # 1. brightness increases sinusoidal between wakeup and noon (rather quick)
        if t_wake < t_now <= t_noon:
            b = 1/2 * self.phase(t_wake, t_now, t_noon)

        # 2. brightness decreases sinusoidal from noon to bedtime (rather slow)
        elif t_noon < t_now < t_sleep:
            b = 1/2 * pi + 1/2 * self.phase(t_noon, t_now, t_sleep)

        # 3. brightness is low (dimmed) during the night
        else:
            b = 0

        # 4. maximum CCT during day cycle as a default
        cct_max = self.cct_sun

        # 5. CCT is lowest between wakeup and sunrise (e.g. in winter)
        if t_wake <= t_now < t_rise:
            f = 0

        # 6. CCT is lowest between sunset and sleeptime (e.g. in winter)
        elif t_set < t_now <= t_sleep:
            f = 0

        # 7. CCT follows sinusoidal curve between sunrise and set
        elif t_rise <= t_now <= t_set:
            f = self.phase(t_rise, t_now, t_set)

        # 8. CCT follows sinusoidal curve at night, this is late night
        elif t_end < t_now < t_start_1:
            f = self.phase(t_end, t_now, t_start_1)
            cct_max = self.cct_moon

        # 9. idem, but for early morning
        elif t_end_0 < t_now < t_start:
            f = self.phase(t_end_0, t_now, t_start)
            cct_max = self.cct_moon

        else:
            print(t_now)
            return

        # 10 linearize the scale via MIREK, otherwise CCT is almost always (very) high
        mirek = sin(f) * (MIREK/cct_max - MIREK/self.cct_min) + MIREK/self.cct_min
        brightness = sin(b) * (self.br_max - self.br_dim) + self.br_dim
        return round(MIREK/mirek), round(brightness)
    



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

    test.eq([(6357,  2), (8720,  2), (10000, 2), (8720,  2), (6357,  2), (4471,  2), (3254, 2), # night
             (2500,  2), (2655, 34), (3471, 62), (4605, 84), (5710, 97), (5930, 99),            # morning
             (5032, 97), (3837, 92), (2903, 84), (2500, 74),                                    # afternoon
             (2500, 62), (2500, 49), (2500, 34), (2500, 18),                                    # evening
             (2500,  2), (3254,  2), (4471,  2),                                                # late night
        ],
        [c.cct_brightness(datetime(2023, 1, 1, hour=h, tzinfo=utc)) for h in range(24)], diff=test.diff) 

    test.eq([(5788,  2), (8967,  2), (9652,  2), (6645,  2), (4107,  2), (2737,  2), (2717,  2),
             (3072,  2), (3502,  2), (4006, 29), (4566, 53), (5135, 74), (5629, 89), (5940, 97), (5981, 99),
             (5741, 96), (5288, 90), (4729, 80), (4160, 68), (3638, 54), (3186, 38), (2811, 20), (2505, 2),
             (3623, 2),
        ],
        [c.cct_brightness(datetime(2023, 6, 21, hour=h, tzinfo=ams)) for h in range(24)],
        diff=test.diff) 

    # in summer, lowest CCT and brightness should be precisely on sun rise or set
    test.eq((2500, 2), c.cct_brightness(datetime(2023, 6, 21, hour= 5, minute=16, tzinfo=ams)))
    test.eq((2500, 2), c.cct_brightness(datetime(2023, 6, 21, hour=22, minute= 1, tzinfo=ams)))

    # in summer, higest CCT should be at sun transit and middle bwteen set and rise
    test.eq(( 6000, 99), c.cct_brightness(datetime(2023, 6, 21, hour=13, minute=39, tzinfo=ams)))
    test.eq((10000,  2), c.cct_brightness(datetime(2023, 6, 22, hour= 1, minute=39, tzinfo=ams)))

    # in winter, lowest CTT should be between wake and rise
    test.eq((2500,  2), c.cct_brightness(datetime(2023, 12, 21, hour= 8, tzinfo=ams)))
    test.eq((2500, 25), c.cct_brightness(datetime(2023, 12, 21, hour= 8, minute=42, tzinfo=ams)))
    # and set and sleep
    test.eq((2500, 79), c.cct_brightness(datetime(2023, 12, 21, hour=16, minute=28, tzinfo=ams)))
    test.eq((2500,  2), c.cct_brightness(datetime(2023, 12, 21, hour=22, tzinfo=ams)))

    # in winter, higest value should be at sun transit and middle bwteen sleep and wake
    test.eq(( 6000, 99), c.cct_brightness(datetime(2023, 12, 21, hour=12, minute=35, tzinfo=ams)))
    test.eq((10000,  2), c.cct_brightness(datetime(2023, 12, 22, hour= 3, tzinfo=ams)))


@test
def real_cycle():
    ams = ZoneInfo('Europe/Amsterdam')
    c = cct_cycle(
        lat      = "52:01.224",
        lon      =  "5:41.065",
        t_wake   = time(hour= 6, tzinfo=ams),
        t_sleep  = time(hour=23, tzinfo=ams),
        cct_min  =  2000,
        cct_sun  =  5000,
        cct_moon = 20000,
        br_dim   =    10,
        br_max   =   100)

    cct, br = c.cct_brightness()
    test.contains(range(1000, 5001), cct) # it just depends on when you run this test
    test.contains(range(10, 101), br)



