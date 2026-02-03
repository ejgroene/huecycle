import requests
import numbers
import cachetools
import functools
import operator
import logging
import contextlib
import datetime

from observable import Observable
from utils import paths, update

import selftest
test = selftest.get_tester(__name__)

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
                    yield path, round(v) # we could normalize value to None, because of
                                     # intermediate dimming levels reported by the bridge
                                     # so, we consider all dimming events ours, for 60s!
                                     # that is LONG, because Circadian might update every
                                     # minute, giving no one else a change

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
        self.recent_paths = cachetools.TTLCache(maxsize=10, ttl=5)
        self.externally_controlled = set()
        super().__init__(**kwargs)

    def __repr__(self):
        return repr(self._key)

    def send(self, message, force=False):
        # this actually receives messages from the Bridge event loop....
        for path, value in normalized_paths(message):
            if self.recent_paths.get(path, '--boo--') != value:
                if path not in self.externally_controlled:
                    logging.info(f"{self}: External control: {path} = {value}")
                self.externally_controlled.add(path)
            update(self._data, path, value)
        # then we forward the message to the observers, for example listeners to sensors
        super().send(message, force=force)

    def receive(self, message, force=False):
        # this actually sends messages to the bridge....
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

