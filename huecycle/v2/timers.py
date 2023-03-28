import datetime
import asyncio

from prototype3 import prototype

import autotest
test = autotest.get_tester(__name__)


one_day = datetime.timedelta(days=1)

def at_time_do(t, callback, dt=datetime):
    assert isinstance(t, datetime.time)
    t = datetime.datetime.combine(dt.datetime.now(), t)
    async def timer_task():
        nonlocal t
        while True:
            s = (t - dt.datetime.now()).total_seconds()
            print("sleeping:", s)
            await asyncio.sleep(s)
            callback()
            t += one_day
    return asyncio.create_task(timer_task())   


class datetime_mock(prototype):
    @property
    def datetime(self):
        return self
    def now(self):
        return datetime.datetime(*self._now)


@test
async def one_timer():
    calls = []
    def wakeup():
        calls.append(1)
    dt_mock = datetime_mock(_now=(2000,1, 1 ,6,59,59,950000))
    t = at_time_do(datetime.time(7,00), wakeup, dt=dt_mock)
    await asyncio.sleep(0)
    test.eq([], calls)
    dt_mock._now = 2000,1, 2 ,6,59,59,950000
    await asyncio.sleep(0.05)
    test.eq([1], calls)
    await asyncio.sleep(0.05)
    test.eq([1, 1], calls)


@test
async def timer_next_day():
    calls = []
    def tobed():
        calls.append(1)
    dt_mock = datetime_mock(_now=(2000,1, 1 , 23,59,59,950000))
    t = at_time_do(datetime.time(00,00,00,50000), tobed, dt=dt_mock)
    await asyncio.sleep(0)
    test.eq([], calls)
    await asyncio.sleep(0.1)
    test.eq([1], calls)
    
    
