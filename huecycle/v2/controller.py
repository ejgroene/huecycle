import asyncio
import time

from observable import Observable
from utils import logexceptions

import selftest
test = selftest.get_tester(__name__)


""" Hue controllers can handle SSE 'events' from the Hue bridge using small 'responders'
    that send 'messages' to their own message 'handler'. This class deals with the message
    loop and dispatching messages using a queue.
"""

class Controller(Observable):
    """ A 'live' controller, with its own loop, continuously controlling lights. """

    def start_message_dispatcher(self, msg_handler, timeout_s):
        """ Create a message queue and a dispatch loop meant for responders
            to send messages to their own 'msg_handler'.
        """
        self._msg_queue = asyncio.Queue()
        self._dispatcher = asyncio.create_task(self._message_dispatcher(msg_handler, timeout_s))


    async def _message_dispatcher(self, msg_handler, timeout_s):
        """ Runs a loop reading from msg_queue and dispatching to 'msg_handler'.
            When 'timeout' happens while awaiting the queue, it calls 'msg_handler'
            without a message.
        """
        while True:
            with logexceptions():
                try:
                    msg = await asyncio.wait_for(self._msg_queue.get(), timeout=timeout_s)
                except asyncio.TimeoutError:
                    msg = {}
                else:
                    self._msg_queue.task_done()
                # Call handler with unpacked msg, to make responders and handlers shorter.
                msg_handler(**msg)


    def dispatch_message(self, **msg):
        """ Send message to own handler, packing msg. """
        self._msg_queue.put_nowait(msg)


    def stop_dispatcher(self):
        self._dispatcher.cancel()


@test
async def controller_basics():
    log = []
    class MyController(Controller):
        def my_handler(self, a=None):
            log.append(a)
    c = MyController()
    c.start_message_dispatcher(c.my_handler, 1)
    try:
        c.dispatch_message(a=42)
        c.dispatch_message(a=43)
        await asyncio.sleep(0.01) # yield CPU
        test.eq([42, 43], log)
    finally:
        c.stop_dispatcher()
    test.truth(c._msg_queue.empty())


class FaultyController(Controller):
    def my_handler(self, a=None):
        raise Exception('faulty')


@test
async def handler_exception_is_logged(stderr):
    c = FaultyController()
    c.start_message_dispatcher(c.my_handler, 1)
    try:
        c.dispatch_message(a=42)
        await asyncio.sleep(0.01) # yield CPU
        err = stderr.getvalue()
        test.startswith(err, "Traceback (most recent call last):\n  File ")
        test.endswith(err, "in my_handler\n    raise Exception('faulty')\nException: faulty\n")
    finally:
        c.stop_dispatcher()


@test
async def invalid_args_is_logged(stderr):
    c = FaultyController()
    c.start_message_dispatcher(c.my_handler, 1)
    try:
        c.dispatch_message(invalid=42)
        await asyncio.sleep(0.01) # yield CPU
        err = stderr.getvalue()
        test.contains(err, "TypeError: FaultyController.my_handler() got an unexpected keyword argument \'invalid\'")
    finally:
        c.stop_dispatcher()


@test
async def controller_timeout():
    log = []
    class MyController(Controller):
        def my_handler(self, a='default a'):
            log.append((a, time.monotonic()))
    c = MyController()
    c.start_message_dispatcher(c.my_handler, 0.01)
    try:
        while len(log) < 2:
            await asyncio.sleep(0) # should timeout 2 times
        test.eq(['default a', 'default a'], [l[0] for l in log])
        test.gt(log[1][1] - log[0][1], 0.008)
        test.lt(log[1][1] - log[0][1], 0.012)
    finally:
        c.stop_dispatcher()
