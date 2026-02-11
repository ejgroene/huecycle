import time
import selftest
test = selftest.get_tester(__name__)


class TimeDict:

    def __init__(self):
        self._d = {}

    def add(self, key, value, time_ms):
        now = time.monotonic_ns()
        self._d[key] = (now + 1e6 * time_ms), value

    def get(self, key, default=None):
        return self._d.get(key, (None, default))[1]

    def expire(self):
        now = time.monotonic_ns()
        self._d = {k: v for k, v in self._d.items() if v[0] > now}


@test
def timedict_basics():
    d = TimeDict()
    d.add('key 1', 'value 1', 1) # ms
    d.add('key 2', 'value 2', 2) # ms
    d.add('key 3', 'value 3', 3) # ms
    test.eq('value 1', d.get('key 1'))
    test.eq('value 2', d.get('key 2'))
    test.eq('value 3', d.get('key 3'))
    time.sleep(0.001)
    d.expire()
    test.eq(None, d.get('key 1'))
    test.eq('value 2', d.get('key 2'))
    test.eq('value 3', d.get('key 3'))
    time.sleep(0.001)
    d.expire()
    test.eq(None, d.get('key 1'))
    test.eq(None, d.get('key 2'))
    test.eq('value 3', d.get('key 3'))
    time.sleep(0.001)
    d.expire()
    test.eq(-1, d.get('key 1', -1))
    test.eq(False, d.get('key 2', False))
    test.eq('nope', d.get('key 3', 'nope'))


