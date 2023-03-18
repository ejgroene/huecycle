import inspect
import asyncio
from datetime import time, datetime, timedelta
from prototype3 import prototype
from extended_cct import ct_to_xy, MIREK

import autotest
test = autotest.get_tester(__name__)


def controller(control):
    """ decorator for marking a function as Hue controller
        'control' must must be a function accepting a Hue service
        object as its first argument. It may be async.
    """
    if inspect.iscoroutinefunction(control):
        def control_func(service, *a, **kw):
            assert hasattr(service, 'type'), service
            assert service.type in ('light', 'grouped_light'), service.type

            """
                What happens when a async controller sets another async controller?
                It must terminate and leave the new one running? Kind of continuation?
                As it is now, the async controller setting a new one gets cancelled while
                doing it.
            """
            try:
                service.controller.cancel()
            except AttributeError:
                pass
            service.controller = asyncio.create_task(control(service, *a, **kw), name=control.__name__)
            return service.controller
    else:
        def control_func(service, *a, **kw):
            if c := service.controller:
                if not c.get_coro().cr_running:
                    c.cancel()
                    del service['controller']
            return control(service, *a, **kw)
    return control_func


@test.fixture
def mockservice(t='light'):
    class service(prototype):
        type = t
        v = []
        def put(self, v):
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
            return prototype('mockcoro', cr_running=False)
    mockservice.controller = mocktask
    @controller
    def do_something(light, x=8):
        light.put('ON') 
    do_something(mockservice, 5)
    test.not_(mockservice.controller)


@test
async def simple_controller_does_NOT_remove_running_task(mockservice):
    @controller
    def do_something(light, x=8):
        light.put('ON') 
    @controller
    async def do_something_repeatedly(light):
        for i in range(3):
            do_something(light, i)
            await asyncio.sleep(0)

    do_something_repeatedly(mockservice)
    await asyncio.sleep(0.01)
    test.eq(['ON', 'ON', 'ON'], mockservice.v)
    test.eq('do_something_repeatedly', mockservice.controller.get_coro().__name__)



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
    test.eq('b_control', task0.get_coro().cr_code.co_name)
    test.truth(task0.done())
    test.not_(task0.cancelled())

    @controller
    async def c_control(service, c=42):
        await asyncio.sleep(0.01)

    task1 = c_control(mockservice)
    test.eq(task1, mockservice.controller)
    test.eq('c_control', task1.get_name())
    test.eq('c_control', task1.get_coro().cr_code.co_name)

    c_control(mockservice)
    await asyncio.sleep(0)
    task2 = mockservice.controller
    test.truth(task1.cancelled())


@controller
def dim(light, brightness=None, delta=None):  # TODO test
    if light.on.on:
        if brightness:
            light.put({'dimming': {'brightness': brightness}})
        elif delta:
            action = 'down' if delta < 0 else 'up'
            delta = abs(delta)
            light.put({'dimming_delta': {'action': action, 'brightness_delta': delta}})


@controller
def light_on(light, ct=3000, brightness=100, use_extended_cct=True):
    if use_extended_cct:
        x, y = ct_to_xy(ct)
        light.put({
            'on': {'on': True},
            'color': {'xy': {'x': x, 'y': y}},
            'dimming': {'brightness': brightness}
        })
    else:
        light.put({
            'on': {'on': True},
            'color_temperature': {'mirek': MIREK//ct},
            'dimming': {'brightness': brightness}
        })


@test
def light_on_test(mockservice:'light'):
    light_on(mockservice)
    test.eq({'on': {'on': True},
             'color': {'xy': {'x': 0.4366, 'y': 0.4042}},
             'dimming': {'brightness': 100}},
         mockservice.v[0])
    light_on(mockservice, ct=2000, brightness=50)
    test.eq({'on': {'on': True},
             'color': {'xy': {'x': 0.5269, 'y': 0.4133}},
             'dimming': {'brightness': 50}},
         mockservice.v[1])
    

@controller
async def light_off(light, after=0, duration=None):
    await asyncio.sleep(after)
    if duration:
        light.put({ 'on': {'on': False}, 'dynamics': {'duration': duration}})
    else:
        light.put({ 'on': {'on': False}})


@test    
async def light_off_test(mockservice):
    light_off(mockservice)
    await asyncio.sleep(0.001)
    test.eq(1, len(mockservice.v))
    test.eq({'on': {'on': False}}, mockservice.v[0])
    light_off(mockservice, after=0.01, duration=1000)
    await asyncio.sleep(0.001)
    test.eq(1, len(mockservice.v))
    await asyncio.sleep(0.01)
    test.eq({'on': {'on': False}, 'dynamics': {'duration': 1000}}, mockservice.v[1])



@controller
async def cycle_cct(light, ct_cycle, t=2*60, use_extended_cct=True):
    while True:
        light_on(light, *ct_cycle.cct_brightness(), use_extended_cct=use_extended_cct)
        await asyncio.sleep(t)



@test.fixture
def mockcycle():
    class cycle(prototype):
        cct_br = iter((ct, br) for ct, br in ((3000, 50), (3100, 60), (4000, 80), (5000, 100)))
        def cct_brightness(self):
            return next(self.cct_br)
    yield cycle


@test
async def cct_controller(mockservice, mockcycle):
    cycle_cct(mockservice, mockcycle, t=0.01)
    await asyncio.sleep(0)
    test.eq(1, len(mockservice.v))
    test.eq({'on': {'on': True}, 'color': {'xy': {'x': 0.4366, 'y': 0.4042}}, 'dimming': {'brightness': 50}}, mockservice.v[0])
    test.eq(False, mockservice.controller.done())

    await asyncio.sleep(0)
    test.eq(1, len(mockservice.v))

    await asyncio.sleep(0.01)
    test.eq(2, len(mockservice.v))
    test.eq({'on': {'on': True}, 'color': {'xy': {'x': 0.4297, 'y': 0.4017}}, 'dimming': {'brightness': 60}}, mockservice.v[1])
    test.eq(False, mockservice.controller.done())

@test
async def cct_cycle_with_group(mockservice:'grouped_light', mockcycle):
    cycle_cct(mockservice, mockcycle, t=0.01)


   
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
    test.eq('do_it', x.get_name())
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
