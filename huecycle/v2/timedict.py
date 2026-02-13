import time
import selftest
test = selftest.get_tester(__name__)


""" A very simple dictionary with expiration time per value and multiple values per key.
    As existing implementations are unmaintained or do not have expiration per key,
    we roll our own.

    It is dead simple and not efficient. You have to call expire().

    Note that it leaves the keys in the dict, even when it has no more values.
"""

class TimeDict:

    def __init__(self):
        self._d = {}

    def put(self, key, value, time_ms):
        now = time.monotonic_ns()
        self._d.setdefault(key, []).append((now + 1e6 * time_ms, value))

    def get(self, key):
        return [value for t, value in self._d.get(key, ())]

    def expire(self):
        now = time.monotonic_ns()
        for values in self._d.values():
            i = 0
            while i < len(values):
                if values[i][0] < now:
                    del values[i]
                else:
                    i += 1

    def __repr__(self):
        now = time.monotonic_ns()
        d = {key: [(round((t - now) / 1e6), v) for (t, v) in values] for key, values in self._d.items()}
        return f"TimeDict{d}"


@test
def timedict_basics():
    d = TimeDict()
    test.eq([], d.get('nonexistent'))
    d.put('key 1', 'value 1', 1) # ms
    d.put('key 2', 'value 2', 2) # ms
    d.put('key 3', 'value 3', 3) # ms
    test.eq("TimeDict{'key 1': [(1, 'value 1')], 'key 2': [(2, 'value 2')], 'key 3': [(3, 'value 3')]}", str(d))
    test.eq(['value 1'], d.get('key 1'))
    test.eq(['value 2'], d.get('key 2'))
    test.eq(['value 3'], d.get('key 3'))
    time.sleep(0.0009) # 1 ms, minus some time for processing this test
    d.expire()
    test.eq("TimeDict{'key 1': [], 'key 2': [(1, 'value 2')], 'key 3': [(2, 'value 3')]}", str(d))
    test.eq([], d.get('key 1'))
    test.eq(['value 2'], d.get('key 2'))
    test.eq(['value 3'], d.get('key 3'))
    time.sleep(0.0009)
    d.expire()
    test.eq("TimeDict{'key 1': [], 'key 2': [], 'key 3': [(1, 'value 3')]}", str(d))
    test.eq([], d.get('key 1'))
    test.eq([], d.get('key 2'))
    test.eq(['value 3'], d.get('key 3'))
    time.sleep(0.0009)
    d.expire()
    test.eq("TimeDict{'key 1': [], 'key 2': [], 'key 3': []}", str(d))
    test.eq([], d.get('key 1'))
    test.eq([], d.get('key 2'))
    test.eq([], d.get('key 3'))
    test.eq(repr(d), str(d))


@test
def expiry_per_value_for_same_key():
    d = TimeDict()
    d.put('key 1', 'value 1', 3) # ms
    d.put('key 1', 'value 2', 1) # ms
    d.put('key 1', 'value 3', 2) # ms
    d.expire()
    test.eq(['value 1', 'value 2', 'value 3'], d.get('key 1'))
    time.sleep(0.0009)
    d.expire()
    test.eq(['value 1', 'value 3'], d.get('key 1'))
    time.sleep(0.0009)
    d.expire()
    test.eq(['value 1'], d.get('key 1'))
    time.sleep(0.0009)
    d.expire()
    test.eq([], d.get('key 1'))

