import inspect
import asyncio
import random
import time
import statistics
from datetime import datetime, timedelta
from prototype3 import prototype
from extended_cct import ct_to_xy, MIREK

import selftest

test = selftest.get_tester(__name__)

""" A controller is a Python function that controls a light using PUT messages.
    It may be async, in which case it is run as a background task. Otherwise,
    the function is simply called once.

    Activation of a new controller cancels the previous one automatically. One
    caveat: one controller may be running for a single light, and another
    controller may be running for a group the light is in.
    These might interfere, as setting a controller for a group does not cancel the
    one for the single light or vice versa.

    A controller must accept a service (light of grouped_light) as the first argument.
    Other argumenst are free to use for other purposes.

    A contoller is activated by simply calling it. For example:

    light_on(my_light, ct=3000)
    cycle_cct(my_light, my_circadian_cycle)
    dim(my_light, delta=-20)

    You define your own contoller using @controller for the function definition. Below
    are some predefined controller for frequently used functions.
"""

__all__ = ["controller", "light_on", "light_off", "dim", "scene_on", "cycle_cct"]


def controller(control):
    """Decorator for marking a function as Hue controller.
    'control' must must be a function accepting a Hue service object as its first argument.
    """

    # if control is a coroutine, schedule a task and attach it to the service
    if inspect.iscoroutinefunction(control):

        def control_func(service, *a, **kw):
            assert hasattr(service, "type"), service
            assert service.type in ("light", "grouped_light"), service.type

            # first cancel the old controller, if any
            # TODO leave this to the new task so it can decide to leave it running
            #      while it wait for its own action to start (e.g. turn off)
            try:
                service.controller.cancel()
            except AttributeError:
                pass

            # start new controller and attach it
            service.controller = asyncio.create_task(
                control(service, *a, **kw), name=control.__name__
            )
            return service.controller

    # simple control, doing one action
    else:

        def control_func(service, *a, **kw):
            # if an async controller is present...
            if c := service.controller:
                # if it is running, it is issueing this command, so leave it alive
                if not c.get_coro().cr_running:
                    c.cancel()
                    del service["controller"]

            return control(service, *a, **kw)

    return control_func


@test.fixture
def mockservice(t="light"):
    class service(prototype):
        on = {"on": False}
        color = {"xy": {"x": 0, "y": 0}}
        dimming = {"brightness": 1}
        dimming_delta = {"action": "down", "brightness_delta": 20}
        type = t
        v = []

        def put(self, v):
            self.update(v.items())
            self.v.append(v)

    yield service


@test
def simple_controller_handling(mockservice):
    @controller
    def a_control(service, a, b=10):
        return a, b

    test.eq((2, 10), a_control(mockservice, 2, 10))


@test
def simple_controller_removes_task(mockservice):
    class mocktask(prototype):
        def cancel(self):
            self.cancelled = True

        def get_coro(self):
            return prototype("mockcoro", cr_running=False)

    mockservice.controller = mocktask

    @controller
    def do_something(light, x=8):
        light.put({"ON": "on"})

    do_something(mockservice, 5)
    test.not_(mockservice.controller)


@test
async def simple_controller_does_NOT_remove_running_task(mockservice):
    @controller
    def do_something(light, x=8):
        light.put({"ON": "on"})

    @controller
    async def do_something_repeatedly(light):
        for i in range(3):
            do_something(light, i)
            await asyncio.sleep(0)

    do_something_repeatedly(mockservice)
    await asyncio.sleep(0.01)
    test.eq([{"ON": "on"}, {"ON": "on"}, {"ON": "on"}], mockservice.v)
    test.eq("do_something_repeatedly", mockservice.controller.get_coro().__name__)


@test
async def advanced_controller_handling(mockservice):
    @controller
    async def b_control(service, a, b=42):
        return service, a, b

    test.not_(mockservice.controller)
    task0 = b_control(mockservice, 8, b=9)
    test.eq((mockservice, 8, 9), await task0)
    test.eq(task0, mockservice.controller)
    test.isinstance(task0, asyncio.Task)
    test.eq("b_control", task0.get_coro().cr_code.co_name)
    test.truth(task0.done())
    test.not_(task0.cancelled())

    @controller
    async def c_control(service, c=42):
        await asyncio.sleep(0.01)

    task1 = c_control(mockservice)
    test.eq(task1, mockservice.controller)
    test.eq("c_control", task1.get_name())
    test.eq("c_control", task1.get_coro().cr_code.co_name)

    c_control(mockservice)
    await asyncio.sleep(0)
    task2 = mockservice.controller
    test.truth(task1.cancelled())


@controller
def light_on(light, ct=None, brightness=100):
    """Turn on light, with specific color temperature and brightness,
    with as few Zigbee messages as possible,
    each key is a separate Zigbee message. Assumes light
    is updated with latest state (via events)"""
    msg = {}

    # if it is not on, turn on
    if not light.on.on:
        msg["on"] = {"on": True}

    # if it is a color light, use extended CCT
    if ct:
        if color := light.color:
            x, y = ct_to_xy(ct)
            # and the color is different
            if (color.xy.x, color.xy.y) != (x, y):
                msg["color"] = {"xy": {"x": x, "y": y}}

        # if it supports color temperature only
        elif color_temp := light.color_temperature:
            schema = color_temp["mirek_schema"]
            mirek_max = schema["mirek_maximum"]
            mirek_min = schema["mirek_minimum"]
            mirek = min(mirek_max, max(mirek_min, MIREK // ct))
            # and the temperature is new
            if mirek != color_temp["mirek"]:
                msg["color_temperature"] = {"mirek": mirek}

    # any lamp can dim
    if dimming := light.dimming:
        # so dim if new value
        if dimming.brightness != brightness:
            msg["dimming"] = {"brightness": brightness}

    # if anything, then send it
    if msg:
        light.put(msg)


@test
def light_on_test(mockservice: "light"):
    mirek_schema = {
        "mirek_schema": {
            "mirek_minimum": 153,
            "mirek_maximum": 454,
        }
    }
    light_on(mockservice)
    test.eq({"on": {"on": True}, "dimming": {"brightness": 100}}, mockservice.v[0])
    light_on(mockservice, ct=2000, brightness=50)
    test.eq(
        {"color": {"xy": {"x": 0.5269, "y": 0.4133}}, "dimming": {"brightness": 50}},
        mockservice.v[1],
    )
    del mockservice.color
    mockservice.color_temperature = mirek_schema
    light_on(mockservice, ct=10000, brightness=42)
    test.not_("on" in mockservice.v[2])
    test.eq({"brightness": 42}, mockservice.v[2]["dimming"])
    test.eq({"mirek": 153}, mockservice.v[2]["color_temperature"])
    mockservice.color_temperature = mirek_schema
    light_on(mockservice, ct=1000)
    test.eq({"mirek": 454}, mockservice.v[3]["color_temperature"])
    mockservice.color_temperature["mirek_schema"] = mirek_schema["mirek_schema"]
    test.eq(4, len(mockservice.v))
    light_on(mockservice, ct=1000)  # nothing should happen
    test.eq(4, len(mockservice.v))


@test
def light_on_limits_zigbee_traffic(mockservice: "light"):
    """each key/value in a PUT results in a separate Zigbee message, avoid as much as possible"""
    light_on(mockservice, ct=3000, brightness=100)
    test.eq(
        {
            "on": {"on": True},
            "color": {"xy": {"x": 0.4366, "y": 0.4042}},
            "dimming": {"brightness": 100},
        },
        mockservice.v[0],
    )
    light_on(mockservice, brightness=90)
    test.eq({"dimming": {"brightness": 90}}, mockservice.v[1])
    light_on(mockservice, brightness=90, ct=2000)
    test.eq({"color": {"xy": {"x": 0.5269, "y": 0.4133}}}, mockservice.v[2])
    mockservice.on = {"on": False}
    light_on(mockservice, brightness=90, ct=2000)
    test.eq({"on": {"on": True}}, mockservice.v[3])
    test.eq(4, len(mockservice.v))
    light_on(mockservice, brightness=90, ct=2000)
    test.eq(4, len(mockservice.v))
    light_on(mockservice, brightness=91, ct=2000)
    test.eq(5, len(mockservice.v))
    light_on(mockservice, brightness=91, ct=2001)
    test.eq(6, len(mockservice.v))


@controller
def dim(light, brightness=None, delta=None):
    assert bool(brightness) ^ bool(delta), "specify either brightness or delta"
    assert brightness is None or 0 < brightness <= 100, brightness
    assert delta is None or -100 < delta < 100, delta
    if light.on.on:
        if brightness:
            light_on(light, brightness=brightness)
        elif delta:
            action = "down" if delta < 0 else "up"
            delta = abs(delta)
            dimming_delta = light.dimming_delta
            if (
                dimming_delta.action != action
                or dimming_delta.brightness_delta != delta
            ):
                light.put(
                    {"dimming_delta": {"action": action, "brightness_delta": delta}}
                )


@test
def dim_test(mockservice):
    with test.raises(AssertionError, "specify either brightness or delta"):
        dim(mockservice)
    with test.raises(AssertionError, "specify either brightness or delta"):
        dim(mockservice, delta=0)
    with test.raises(AssertionError, "specify either brightness or delta"):
        dim(mockservice, brightness=0)
    with test.raises(AssertionError, "specify either brightness or delta"):
        dim(mockservice, brightness=50, delta=10)
    with test.raises(AssertionError, "101"):
        dim(mockservice, brightness=101)
    with test.raises(AssertionError, "-1"):
        dim(mockservice, brightness=-1)
    with test.raises(AssertionError, "100"):
        dim(mockservice, delta=+100)
    with test.raises(AssertionError, "-100"):
        dim(mockservice, delta=-100)
    mockservice.on = {"on": True}
    dim(mockservice, delta=-10)
    test.eq(
        {"dimming_delta": {"action": "down", "brightness_delta": 10}}, mockservice.v[0]
    )
    dim(mockservice, delta=+10)
    test.eq(
        {"dimming_delta": {"action": "up", "brightness_delta": 10}}, mockservice.v[1]
    )
    dim(mockservice, brightness=40)
    test.eq({"dimming": {"brightness": 40}}, mockservice.v[2])
    mockservice.on = {"on": False}
    test.eq(3, len(mockservice.v))
    dim(mockservice, brightness=40)
    dim(mockservice, delta=+10)
    test.eq(3, len(mockservice.v))


@test
def dim_avoid_messages(mockservice):
    mockservice.on = {"on": True}
    dim(mockservice, brightness=40)
    test.eq({"dimming": {"brightness": 40}}, mockservice.v[0])
    dim(mockservice, brightness=40)
    test.eq(1, len(mockservice.v))
    dim(mockservice, delta=-10)
    test.eq(
        {"dimming_delta": {"action": "down", "brightness_delta": 10}}, mockservice.v[1]
    )
    dim(mockservice, delta=-10)
    test.eq(2, len(mockservice.v))
    dim(mockservice, delta=+10)
    test.eq(
        {"dimming_delta": {"action": "up", "brightness_delta": 10}}, mockservice.v[2]
    )
    dim(mockservice, delta=+10)
    test.eq(3, len(mockservice.v))
    dim(mockservice, delta=+11)
    test.eq(
        {"dimming_delta": {"action": "up", "brightness_delta": 11}}, mockservice.v[3]
    )


@controller
def scene_on(scene):
    scene.put({"recall": {"action": "active"}})


@test
def scene_on_test(mockservice: "scene"):
    scene_on(mockservice)
    test.eq({"recall": {"action": "active"}}, mockservice.v[0])


@controller
async def light_off(light, after=0, duration=None):
    await asyncio.sleep(after)
    if duration:
        light.put({"on": {"on": False}, "dynamics": {"duration": duration}})
    else:
        light.put({"on": {"on": False}})


@test
async def light_off_test(mockservice):
    light_off(mockservice)
    await asyncio.sleep(0.001)
    test.eq(1, len(mockservice.v))
    test.eq({"on": {"on": False}}, mockservice.v[0])
    light_off(mockservice, after=0.01, duration=1000)
    await asyncio.sleep(0.001)
    test.eq(1, len(mockservice.v))
    await asyncio.sleep(0.01)
    test.eq({"on": {"on": False}, "dynamics": {"duration": 1000}}, mockservice.v[1])


@controller
async def cycle_cct(light, ct_cycle, t=2 * 60):
    while True:
        light_on(light, *ct_cycle.cct_brightness())
        await asyncio.sleep(t)


@test.fixture
def mockcycle():
    class cycle(prototype):
        cct_br = iter(
            (ct, br) for ct, br in ((3000, 50), (3100, 60), (4000, 80), (5000, 100))
        )

        def cct_brightness(self):
            return next(self.cct_br)

    yield cycle


@test
async def cct_controller(mockservice, mockcycle):
    cycle_cct(mockservice, mockcycle, t=0.01)
    await asyncio.sleep(0)
    test.eq(1, len(mockservice.v))
    test.eq(
        {
            "on": {"on": True},
            "color": {"xy": {"x": 0.4366, "y": 0.4042}},
            "dimming": {"brightness": 50},
        },
        mockservice.v[0],
    )
    test.eq(False, mockservice.controller.done())

    await asyncio.sleep(0)
    test.eq(1, len(mockservice.v))

    await asyncio.sleep(0.01)
    test.eq(2, len(mockservice.v))
    test.eq(
        {"color": {"xy": {"x": 0.4297, "y": 0.4017}}, "dimming": {"brightness": 60}},
        mockservice.v[1],
    )
    test.eq(False, mockservice.controller.done())


@test
async def cct_cycle_with_group(mockservice: "grouped_light", mockcycle):
    cycle_cct(mockservice, mockcycle, t=0.01)
    # en?


def timer(t, control, *args, **kwargs):
    dt = (t - datetime.now()).total_seconds()
    assert dt > 0, f"Time lies in the past: {t}"
    assert callable(control), f"control must be callable: {control!r}"
    assert inspect.signature(control).bind(*args, **kwargs)

    # call_at/call_later?
    async def timer_task():
        await asyncio.sleep(dt)
        return control(*args, **kwargs)

    return asyncio.create_task(timer_task(), name=control.__name__)


@test
async def timer_test():
    delta = timedelta(milliseconds=100)

    def do_it(x, a=10):
        return x * a

    t = datetime.now() + delta
    x = timer(t, do_it, 42, a=2)
    test.eq("do_it", x.get_name())
    test.eq(84, await x)
    dt = (datetime.now() - t).total_seconds()
    test.gt(dt, 0.00)


@test
async def timer_checks_args():
    delta = timedelta(milliseconds=100)
    t = datetime.now() - delta
    with test.raises(AssertionError, f"Time lies in the past: {t}"):
        timer(t, None)

    t = datetime.now() + delta
    with test.raises(AssertionError, f"control must be callable: 'aap'"):
        timer(t, "aap")

    def f(a):
        pass

    with test.raises(TypeError, f"missing a required argument: 'a'"):
        timer(t, f)


def randomize(dt, *fns):
    # TODO instead of calling functions at random times, change this to
    #      setting controllers on a services which all wait a given time
    #      this helps making consequtive task scheduling easier, avoiding
    #      lights staying on of off caused by concurrency problems.
    assert isinstance(dt, timedelta)
    call_later = asyncio.get_running_loop().call_later
    uniform = random.uniform
    dt_s = dt.total_seconds()
    for fn in fns:
        delay = uniform(0, dt_s)
        call_later(delay, fn) # if you turn the light off before this is executed,
                              # you must stop the timer; not good...


@test(timeout=10)
async def randomize_test():
    dt_100ms = timedelta(milliseconds=100)
    times = []
    monotonic = time.monotonic
    append = times.append
    t0 = monotonic()

    def a():
        append(monotonic() - t0)

    # 100 times in 100 ms => 1 ms per call
    randomize(dt_100ms, *100 * [a])
    await asyncio.sleep(0.1)
    test.eq(100, len(times))
    # perfect stdev should be slighty larger than 0.03
    test.gt(statistics.stdev(times), 0.025)


def on_motion(sensor, on, off):
    @sensor.handler
    def handle(sensor, event):
        if event.get("motion"):
            on()
        else:
            off()


@test
def precedence_options():
    @controller
    async def override(light):
        # default: replace current controller
        pass

    @controller
    async def later(light):
        # when current controller ends (when does that happen?)
        pass

    @controller
    async def at_time(light):
        # keep current controller; i'll kill it miself
        pass
