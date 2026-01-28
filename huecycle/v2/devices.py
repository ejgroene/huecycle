import requests
import numbers
import cachetools
import functools
import operator
import logging
import contextlib
import datetime

from observable import Observable

import selftest
test = selftest.get_tester(__name__)

def paths(d):
    for k, v in d.items():
        path = k,
        if isinstance(v, dict):
            for p, v in paths(v):
                yield path + p, v
        else:
            yield path, v

def update(d, path, value):
    for p in path[:-1]:
        d = d.setdefault(p, {})
    d[path[-1]] = value

@test
def as_dicts_basisc():
    d = {}
    update(d, (1,), 42)
    test.eq({1: 42}, d)
    d = {}
    update(d, (1, 2), 42)
    test.eq({1: {2: 42}}, d)
    d = {1: {2: {3:9}, 4:12}, 5:17}
    update(d, (1, 2, 3), 42)
    test.eq({1: {2: {3:42}, 4:12}, 5:17}, d)

@test
def paths_basic():
    test.eq([], list(paths({})))
    test.eq([((1,), 2)], list(paths({1: 2})))
    test.eq([((1,), 2), ((2,), 3)], list(paths({1: 2, 2: 3})))
    test.eq([((1, 2), 3)], list(paths({1: {2: 3}})))
    test.eq([((1, 2, 3), 4)], list(paths({1: {2: {3: 4}}})))

def normalized_paths(p):
    for path, v in paths(p):
        match path:
            case ('type', ) | \
                 ('button', 'last_event') | \
                 ('button', 'button_report', 'event') | \
                 ('button', 'button_report', 'updated') | \
                 ('light', 'light_level_report', 'changed') | \
                 ('light', 'light_level_valid') | \
                 ('motion', 'motion_report', 'changed') | \
                 ('motion', 'motion_report', 'motion') | \
                 ('motion', 'motion_valid') | \
                 ('color_temperature', 'mirek_valid') | \
                 ('status', 'last_recall') | \
                 ('dynamics', 'status') | \
                 ('dynamics', 'speed') | \
                 ('dynamics', 'speed_valid'):
                pass

            case ('on', 'on') | \
                 ('motion', 'motion') | \
                 ('color', 'xy', 'x') | \
                 ('color', 'xy', 'y') | \
                 ('color_temperature', 'mirek') | \
                 ('light', 'light_level') | \
                 ('light', 'light_level_report', 'light_level') | \
                 ('status', 'active') | \
                 ('actions',) | \
                 ('dynamics', 'duration'):
                yield path, v

            case ('dimming', 'brightness'):
                if v != 0.0: # Turning off results in a brightness=0.0 event
                    yield path, round(v)

            case _:
                raise Exception((path, v))

class Device(Observable):

    def __init__(self, data, key, put, **kwargs):
        self._data = data
        self._key = key
        self._put = put
        # TTL: 25 includes the ~20s 'heartbeat' repeating old events
        # We've also seen events being echoed 60s later....
        # It doesn't really matter though, as long as we know what we did ourselves,
        # and it somehow gradually disappears.
        self.recent_paths = cachetools.TTLCache(maxsize=10, ttl=60)
        self.externally_controlled = set()
        super().__init__(**kwargs)

    def __repr__(self):
        return repr(self._key)

    def send(self, message, force=False):
        for path, value in normalized_paths(message):
            if self.recent_paths.get(path, '--boo--') != value:
                logging.info(f"{self}: External control: {path} = {value}")
                self.externally_controlled.add(path)
            update(self._data, path, value)
        super().send(message, force=force)

    def receive(self, message, force=False):
        to_send = {}
        for path, value in normalized_paths(message):
            if path in self.externally_controlled:
                if not force:
                    logging.info(f"{self}: Ignoring {path} = {value}")
                    continue
                logging.info(f"{self}: Controlling {path} = {value}")
                self.externally_controlled.remove(path)
            self.recent_paths[path] = value
            update(to_send, path, value)
        if to_send:
            type, id = self._data['type'], self._data['id']
            self._put(f"{type}/{id}", to_send)


@test
def device_basics():
    d = Device({}, 'key1', None)
    test.truth(isinstance(d, Observable))
    test.eq("'key1'", repr(d))
    test.eq("'key1'", str(d))
    d.add_observer(None)
    test.eq([None], d._observers)

@test
def device_receive():
    put_args = []
    def put(path, json, **kwargs):
        put_args.append((path, json, kwargs))

    d = Device({'type': 'light', 'id': '3456'}, 'key1', put)
    d.receive({'type': 'light', 'on': {'on': True}})
    test.eq([('light/3456', {'on': {'on': True}}, {})], put_args)

