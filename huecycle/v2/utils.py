import asyncio
import contextlib
import traceback

from observable import Observable

async def sleep(seconds=0):
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.sleep(seconds)

def clamp(x, lo, hi):
    return int(max(lo, min(hi, x)))


class Adapt(Observable):

    def __init__(self, **mapping):
        self._mapping = mapping
        super().__init__()

    def receive(self, msg, **kwargs):
        name = msg['type']
        name = self._mapping.get(name, name)
        self.send(dict(msg, type=name), **kwargs)


@contextlib.contextmanager
def logexceptions(exception=Exception):
    try:
        yield
    except KeyboardInterrupt:
        raise
    except exception as e:
        traceback.print_exception(e)
