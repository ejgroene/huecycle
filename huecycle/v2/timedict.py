import time
import selftest
test = selftest.get_tester(__name__)


""" A very simple dictionary with expiration time per key.
    As existing implementations are unmaintained or do not have
    expiration per key, we roll our own.

    It is dead simple and not efficient. You have to call expire()!
"""

class TimeDict:

    def __init__(self):
        self._d = {}

    def put(self, key, value, time_ms):
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
    d.put('key 1', 'value 1', 1) # ms
    d.put('key 2', 'value 2', 2) # ms
    d.put('key 3', 'value 3', 3) # ms
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


