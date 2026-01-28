import asyncio
import contextlib
import traceback


async def sleep(seconds=0):
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.sleep(seconds)


def clamp(x, lo, hi):
    return int(max(lo, min(hi, x)))


@contextlib.contextmanager
def logexceptions(exception=Exception):
    try:
        yield
    except KeyboardInterrupt:
        raise
    except exception as e:
        traceback.print_exception(e)
