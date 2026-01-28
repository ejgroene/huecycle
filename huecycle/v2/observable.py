
""" Simple implementation of the Observable pattern.
    Observers can send and receive messages.
    Default send() dispatches to receivei() of the observers.
    Default receive() dispatches to named handlers on self, based on the
        type of the message.
"""

import inspect
import warnings
import logging

import selftest
test = selftest.get_tester(__name__)

class Observable:

    def __init__(self, **message_map):
        self._observers = []
        self._initialized = False
        self._message_map = message_map

    def add_observer(self, observer):
        self._observers.append(observer)

    def init_all(self):
        if not self._initialized:
            self.init()
            self._initialized = True
        for o in self._observers:
            o.init_all()

    def init(self):
        pass

    def send(self, msg, **kwargs):
        if isinstance(msg, dict):
            type_org = msg.get('type')
            type_new = self._message_map.get(type_org, type_org)
            if type_new != type_org:
                logging.info(f"Mapping type {type_org} to {type_new}")
                msg = dict(msg, type=type_new)
        for o in self._observers:
            o.receive(msg, **kwargs)

    def receive(self, msg, force=None):
        if isinstance(msg, dict):
            if type := msg.get('type'):
                if method := getattr(self, type, None):
                    if inspect.ismethod(method):  #TODO test
                        return method(**{k:msg[k] for k in msg if k != 'type'})
        if method := getattr(self, 'unknown', None):
            return method(msg)  #TODO test
        warnings.warn(f"{self} does not understand {msg}")

# TODO test me
def be(factory, component, *observers, seen=set()):
    if component in seen:
        return component, seen
    seen.add(component)
    for x in observers:
        c, *o = x
        c, seen = be(factory, c, *o)
        component.add_observer(c)
    return component, seen



@test
def observable_noop():
    o0 = Observable()
    o1 = Observable()
    o0.add_observer(o1)
    o0.send("message")
    o0.receive("message")
    # nothing happens


@test
def observer_message_send():
    received = []
    class O(Observable):
        def receive(self, message):
            received.append((self, message))
    o0 = Observable()
    o1 = O()
    o2 = O()
    o0.add_observer(o1)
    o0.add_observer(o2)
    o0.send("message")
    test.eq([(o1, 'message'), (o2, 'message')], received)


@test
def observer_message_dispatch():
    received = []
    class O1(Observable):
        def one(self, message):
            received.append((1, message))
    class O2(Observable):
        def two(self, message):
            received.append((2, message))
    o0 = Observable()
    o1 = O1()
    o2 = O2()
    o0.add_observer(o1)
    o0.add_observer(o2)
    with warnings.catch_warnings(record=True) as w:
        o0.send({'type': 'one', 'message': 'hello one'})
        o0.send({'type': 'two', 'message': 'hello two'})
        test.eq([(1, 'hello one'), (2, 'hello two')], received)
        test.eq(2, len(w))
        test.contains(w[0].message.args[0], "does not understand")
        test.contains(w[1].message.args[0], "does not understand")

@test
def message_map():
    log = []
    class O1(Observable):
        pass
    class O2(Observable):
        def g(self, a):
            log.append(a)

    o1 = O1(f='g')
    o2 = O2()
    o1.add_observer(o2)
    o1.send({'type': 'f', 'a': 42})
    test.eq([42], log)

