import logging

from observable import Observable
from utils import paths, update, logexceptions, DontCare
from timedict import TimeDict

import selftest
test = selftest.get_tester(__name__)


""" Device represents devices found in a Hue Bridge and functions as a per device gateway.

    It receives messages from the Bridge's eventstream (SSE) which are dispatched
    to its observers.

    It receives messages from other Observers, which are sent to the Bridge.

    Device goes through lengths to register what is sent to the bridge, such that it can
    tell events received from the Bridge as being responses to its own actions.

    Any events not recognized are registered as 'external' and subsequently ignored, as to
    respect external controllers' (e.g. the app) settings.
"""

def normalized_paths(message):
    """ Splits a hierarchical dict (message) into paths with one value.
        Each path + value is dealt with separately to handle quirks.
        It yields a retention time, path and (possibly) normalized value.
        The retention time is meant for considering a specific path as
        resulting from our own actions.
    """

    for path, value in paths(message):
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
                yield 20, path, value

            case ('dimming', 'brightness'):
                # Turning off results in a brightness=0.0 event, we never send it ourselves
                if value != 0.0:

                    # The bridge reports intermediate dimming levels, while we
                    # sollicitated only one. To avoid triggering 'external control'
                    # we consider all dimming events ours for 20s, by means of DontCare
                    yield 20, path, DontCare(round(value))

                    # We also yield the exact value which we hold on much longer, as the
                    # bridge sometimes repeats old events up to one minute later.
                    # We still don't know why (does it happen when turning off??)
                    yield 60, path, round(value)

                    # Note that both path + value are identical and will not be duplicated
                    # in the JSON messages sent to the bridge.

            case _:
                raise Exception(f"Unknown path: {path}")


@test
def normalized_paths_basics():
    test.eq([(20, ('on', 'on'), 'Yes')], list(normalized_paths({'on': {'on': 'Yes'}})))
    test.eq([], list(normalized_paths({'dynamics': {'speed': 'S'}})))
    test.eq([], list(normalized_paths({'dimming': {'brightness': 0.0}})))
    brightness = list(normalized_paths({'dimming': {'brightness': 10.6}}))
    test.eq([(20, ('dimming', 'brightness'), 11),
             (60, ('dimming', 'brightness'), 11)],
            brightness)
    dontcare_brightness = brightness[0][2]
    test.eq(42, dontcare_brightness)         # DontCare
    test.eq(99, dontcare_brightness)         # DontCare
    test.eq('11', str(dontcare_brightness))  # Serialization
    real_brightness = brightness[1][2]
    test.eq(11, real_brightness)
    test.isinstance(real_brightness, int)
    with test.raises(Exception, "Unknown path: ('does', 'not')"):
        list(normalized_paths({'does': {'not': 'exist'}}))


class Device(Observable):

    def __init__(self, data, key, put, **kwargs):
        self._data = data
        self._key = key
        self._put = put
        self.recent_paths = TimeDict()
        self.externally_controlled = set()
        super().__init__(**kwargs)

    def __repr__(self):
        return repr(self._key)

    def send(self, message, force=False):
        # this actually receives messages from the Bridge event loop....
        with logexceptions():
            for _, path, value in normalized_paths(message):
                if value not in self.recent_paths.get(path):
                    if path not in self.externally_controlled:
                        logging.info(f"{self}: External control: {path} = {value}")
                    self.externally_controlled.add(path)
                update(self._data, path, value)
            # then we forward the message to the observers, for example listeners to sensors
            super().send(message, force=force)

    def receive(self, message, force=False):
        # this actually sends messages to the bridge....
        to_send = {}
        with logexceptions():
            self.recent_paths.expire()
            for retention_time, path, value in normalized_paths(message):
                if path in self.externally_controlled:
                    if not force:
                        logging.info(f"{self}: Ignoring {path} = {value}")
                        continue
                    logging.info(f"{self}: Controlling {path} = {value}")
                    self.externally_controlled.remove(path)
                # add the value to the path
                self.recent_paths.put(path, value, retention_time * 1000)
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
def happy_flow_receive_send():
    # mock http put from bridge
    put_args = []
    def put(path, json):
        put_args.append((path, json))
    data = {'type': 'my-type', 'id': 'my-id'}
    d = Device(data, 'key', put)

    # receive a msg and send it to the bridge with put
    d.receive({'on': {'on': True}, 'dimming': {'brightness': 45}})
    test.eq([('my-type/my-id', {'on': {'on': True}, 'dimming': {'brightness': 45}})], put_args)

    # no we are being send an event from the bridge (echoing what we sent it)
    received = []
    class MyObserver:
        def receive(self, msg, **kwargs):
            received.append((msg, kwargs))
    d.add_observer(MyObserver())
    test.eq(None, data.get('on'))
    d.send({'type': 'on', 'on': {'on': True}})
    test.eq([({'type': 'on', 'on': {'on': True}}, {'force': False})], received)

    # it also updates the state
    test.eq({'on': True}, data.get('on'))

    # some internals: recents paths
    test.eq([True], d.recent_paths.get(('on', 'on')))
    values = d.recent_paths.get(('dimming', 'brightness'))
    test.eq([99, 45], values) # registerd twice: one DontCare


@test
def ignore_external_control():
    # send
    # receive
    # ignored
    pass

