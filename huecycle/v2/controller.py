import asyncio

from observable import Observable
from utils import logexceptions

class Controller(Observable):

    def start_event_dispatcher(self, handler, timeout):
        self._queue = asyncio.Queue()
        self._task = asyncio.create_task(self._loop(handler, timeout))

    def dispatch_event(self, **attrs):
        self._queue.put_nowait(attrs)

    async def _loop(self, handler, timeout):
        while True:
            with logexceptions():
                try:
                    attrs = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    attrs = {}
                else:
                    self._queue.task_done()
                handler(**attrs)


