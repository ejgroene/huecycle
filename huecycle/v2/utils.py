import asyncio
import contextlib
import traceback
import selftest

test = selftest.get_tester(__name__)


#TODO remove (use queue)
async def sleep(seconds=0):
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.sleep(seconds)


def clamp(x, lo, hi):
    # limit x between lo and hi
    assert lo < hi, f"{lo} > {hi}"
    return int(max(lo, min(hi, x)))

@test
def clamp_basics():
    test.eq( 1, clamp( 1, -1, 1))
    test.eq( 0, clamp( 0, -1, 1))
    test.eq(-1, clamp(-1, -1, 1))
    test.eq( 1, clamp( 2, -1, 1))
    test.eq( 0, clamp( 0, -1, 1))
    test.eq(-1, clamp(-2, -1, 1))
    with test.raises(AssertionError, "3 > 2"):
        clamp(None, 3, 2)
    test.eq( 1, clamp( 1.2, -1.1, 1.1))



@contextlib.contextmanager
def logexceptions(exception=Exception):
    try:
        yield
    except KeyboardInterrupt:
        raise
    except exception as e:
        traceback.print_exception(e)


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

