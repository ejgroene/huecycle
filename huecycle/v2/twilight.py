import statistics
import collections
import datetime as datetime_py
from prototype3 import prototype

import autotest
test = autotest.get_tester(__name__)


# a reasonable window size from experiments with log data
W = 10
noon = datetime_py.time(13,00)


def twilight(sensor, on_dawn, on_dusk, threshold=1000, window_size=W, dt=datetime_py):
    window = collections.deque(maxlen=window_size)
    lock = None

    @sensor.handler
    def detect_twilight(sensor, event):
        nonlocal lock
        level = event['light']['light_level']
        window.append(level)
        avg = round(statistics.mean(window))

        print("LEVEL:", avg, lock)

        # it is dawn
        if dt.datetime.now().time() < noon:
            if lock == 'dawn':
                return
            lock = None
            if avg > threshold:
                on_dawn(sensor, avg)
                lock = 'dawn'

        # it is dusk
        else:
            if lock == 'dusk':
                return
            lock = None
            if avg < threshold:
                on_dusk(sensor, avg)
                lock = 'dusk'

    def is_twilight():
        """ it it still twilight or has the light already been turned on (dusk) or off (dawn)?
            Twilight being either before light (morning) or before dark (evening) """
        return not lock

    return is_twilight
        

    
def ll_event(level):
    return {'light': {
                'light_level': level,
                'light_level_report': {
                    'changed': '2023-03-22T20:19:18.436Z',
                    'light_level': level
                },
                'light_level_valid': True
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
    """ without mocking datetime, see if it does anything at all,
        so we can assure it calls datetime correctly """
    calls = []
    def on_twilight(sensor, avg_ll):
        calls.append((sensor, avg_ll))
    is_twilight = twilight(sensor, on_twilight, on_twilight)
    test.eq(True, is_twilight())
    sensor.event_handler(ll_event(10))
    test.eq([(sensor, 10)], calls)
    test.eq(False, is_twilight())
   
 
@test
def twilight_init():
    dawns = []
    dusks = []
    def on_dawn(sensor, avg_ll):
        dawns.append((sensor, avg_ll))
    def on_dusk(sensor, avg_ll):
        dusks.append((sensor, avg_ll))
    dt_mock = datetime_mock(_now=(2000, 3, 31, 8, 30))
    is_twilight = twilight(sensor, on_dawn, on_dusk, threshold=100, window_size=3, dt=dt_mock)
    sensor.event_handler(ll_event( 50))
    sensor.event_handler(ll_event(150))
    test.eq([], dawns)
    test.eq([], dusks)
    test.eq(True, is_twilight())
    sensor.event_handler(ll_event(102))
    test.eq([(sensor, 101)], dawns)
    test.eq([], dusks)
    test.eq(False, is_twilight())
    # nothing happens anymore
    sensor.event_handler(ll_event(102))
    sensor.event_handler(ll_event(300))
    sensor.event_handler(ll_event( 50))
    sensor.event_handler(ll_event( 25))
    sensor.event_handler(ll_event(100))
    sensor.event_handler(ll_event(100))
    sensor.event_handler(ll_event(200))
    test.eq([(sensor, 101)], dawns)
    test.eq([], dusks)
    test.eq(False, is_twilight())

    dt_mock._now = 2000, 3, 31, 15, 00
    sensor.event_handler(ll_event(100))
    test.eq(True, is_twilight())
    sensor.event_handler(ll_event(50))
    sensor.event_handler(ll_event(50))
    test.eq([(sensor, 101)], dawns)
    test.eq([(sensor, 67)], dusks)
    test.eq(False, is_twilight())
    # nothing happens anymore
    sensor.event_handler(ll_event(500))
    sensor.event_handler(ll_event( 50))
    sensor.event_handler(ll_event( 50))
    sensor.event_handler(ll_event( 50))
    test.eq([(sensor, 101)], dawns)
    test.eq([(sensor, 67)], dusks)
    test.eq(False, is_twilight())
    
