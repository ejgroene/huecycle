import statistics
import collections
import datetime as datetime_py
from prototype3 import prototype

import autotest

test = autotest.get_tester(__name__)


# a reasonable window size from experiments with log data
W = 3
noon = datetime_py.time(13, 00)


def twilight(sensor, on_dawn, on_dusk, threshold=1000, window_size=W, dt=datetime_py):
    window = collections.deque(maxlen=window_size)
    lock = None

    @sensor.handler
    def detect_twilight(sensor, event):
        nonlocal lock
        level = event["light"]["light_level"]
        window.append(level)

        # start up behaviour, do not engage until a certain number of measurements
        if len(window) < window_size // 2:
            return

        avg = round(statistics.mean(window))
        print("AVG LIGHT LEVEL:", avg, lock)

        # it is dawn
        if dt.datetime.now().time() < noon:
            if lock == "dawn":
                return
            lock = None
            if avg > threshold:
                print("DAWN:", avg)
                on_dawn()
                lock = "dawn"

        # it is dusk
        else:
            if lock == "dusk":
                return
            lock = None
            # level below threshold, or 0 (happens, then no more events follow!) #TODO test
            if avg < threshold or level == 0: 
                print("DUSK:", avg)
                on_dusk()
                lock = "dusk"

    def is_twilight():
        """it it still twilight or has the light already been turned on (dusk) or off (dawn)?
        Twilight being either before light (morning) or before dark (evening)"""
        return not lock

    return is_twilight


def ll_event(level):
    return {
        "light": {
            "light_level": level,
            "light_level_report": {
                "changed": "2023-03-22T20:19:18.436Z",
                "light_level": level,
            },
            "light_level_valid": True,
        }
    }


class sensor(prototype):
    def handler(self, f):
        self.event_handler = f


class datetime_mock(prototype):
    time = datetime_py.time

    @property
    def datetime(self, *a, **k):
        return self

    def now(self):
        return datetime_py.datetime(*self._now)


@test
def init_twilight():
    """without mocking datetime, see if it does anything at all,
    so we can assure it calls datetime correctly"""
    calls = []

    def on_twilight():
        calls.append(1)

    is_twilight = twilight(
        sensor, on_twilight, on_twilight, threshold=20, window_size=2
    )
    test.eq(True, is_twilight())
    sensor.event_handler(ll_event(10))  # this one triggers in the morning
    sensor.event_handler(ll_event(50))  # this one in the evening
    test.eq([1], calls)
    test.eq(False, is_twilight())


@test
def wait_for_minimum_number_of_measurements():
    dt_mock = datetime_mock(_now=(2000, 3, 31, 8, 30))
    calls = []

    def on_twilight():
        calls.append(1)

    twilight(sensor, on_twilight, on_twilight, threshold=10, window_size=10, dt=dt_mock)
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(50))
    test.eq([1], calls)


@test
def twilight_event_handling():
    calls = []

    def on_dawn():
        calls.append("dawn")

    def on_dusk():
        calls.append("dusk")

    dt_mock = datetime_mock(_now=(2000, 3, 31, 8, 30))
    is_twilight = twilight(
        sensor, on_dawn, on_dusk, threshold=100, window_size=3, dt=dt_mock
    )
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(150))
    test.eq([], calls)
    test.eq(True, is_twilight())
    sensor.event_handler(ll_event(102))
    test.eq(["dawn"], calls)
    test.eq(False, is_twilight())
    # nothing happens anymore
    sensor.event_handler(ll_event(102))
    sensor.event_handler(ll_event(300))
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(25))
    sensor.event_handler(ll_event(100))
    sensor.event_handler(ll_event(100))
    sensor.event_handler(ll_event(200))
    test.eq(["dawn"], calls)
    test.eq(False, is_twilight())

    dt_mock._now = 2000, 3, 31, 15, 00
    sensor.event_handler(ll_event(100))
    test.eq(True, is_twilight())
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(50))
    test.eq(["dawn", "dusk"], calls)
    test.eq(False, is_twilight())
    # nothing happens anymore
    sensor.event_handler(ll_event(500))
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(50))
    test.eq(["dawn", "dusk"], calls)
    test.eq(False, is_twilight())

@test
def no_more_events_when_0():
    calls = []

    def on_dawn():
        calls.append("dawn")

    def on_dusk():
        calls.append("dusk")

    dt_mock = datetime_mock(_now=(2020, 3, 31, 18, 30))
    is_twilight = twilight(
        sensor, on_dawn, on_dusk, threshold=4000, window_size=5, dt=dt_mock
    )
    sensor.event_handler(ll_event(10000))
    sensor.event_handler(ll_event(10000))
    sensor.event_handler(ll_event(10000))
    sensor.event_handler(ll_event(10000)) # goes down fast
    sensor.event_handler(ll_event( 5000)) # average does no come below threshold
    sensor.event_handler(ll_event(  500)) # and...
    sensor.event_handler(ll_event(    0)) # no more events until next light!
    test.eq(["dusk"], calls)


