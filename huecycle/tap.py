import selftest

test = selftest.get_tester(__name__)

from controllers import cycle_cct, light_off, light_on, dim, scene_on


def setup2(bridge, name, light, cycle, sceneII, sceneIII, sceneIV):
    """
    When off, switches to four scenes:
    1. cycle cct
    2. sceneII
    3. sceneIII
    4. sceneIV
    When on, switches do:        dimmer
    1. turn off                  reset    (4)
    2. dim scene                 brighten (3)
    3. brighten scene            dim      (2)
    4. reset scene               off      (1)
    """
    last_scene = None

    def set_scene(s):
        nonlocal last_scene
        scene_on(s)
        last_scene = s

    def set_cycle():
        nonlocal last_scene
        cycle_cct(light, cycle)
        last_scene = None

    def reset():
        nonlocal last_scene
        if last_scene:
            set_scene(last_scene)
        else:
            set_cycle()

    setup4(
        bridge,
        name,
        light,
        (lambda: set_cycle(), lambda: light_off(light)),
        (lambda: set_scene(sceneII), lambda: dim(light, delta=-25)),
        (lambda: set_scene(sceneIII), lambda: reset()),
        (lambda: set_scene(sceneIV), lambda: dim(light, delta=+25)),
    )


def buttons(byname, name, n=4):
    return [byname(f"{name}:{i}") for i in range(1, 1 + n)]


def setup4(bridge, name, light, *actions):
    n = len(actions)
    btns = buttons(bridge.byname, name, n)

    def make_handler(off, on):
        def handler(service, event):
            """ event once was None #TODO
Traceback (most recent call last):
  File "/Users/admin/dev/huecycle/huecycle/main.py", line 198, in main
    await my_bridge.dispatch_events()
  File "/Users/admin/dev/huecycle/huecycle/bridge.py", line 162, in dispatch_events
    service.event_handler(update)
  File "/Users/admin/dev/huecycle/huecycle/tap.py", line 61, in handler
    if event.button_report.event == "initial_press":
       ^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'event'
"""

            if event.button_report.event == "initial_press":
                action = on if light.on.on else off
                action()

        return handler

    for btn, onoff in zip(btns, actions):
        btn.handler(make_handler(*onoff))


def setup5(device, is_on, *actions):
    n = len(actions)
    name = device.qname.split(":")[-1]
    print("NAME:", name)
    btns = [device.byname(f"button:{name}:{i}") for i in range(1, 1 + n)]

    def make_handler(on, off):
        def handler(service, event):
            if event.button_report.event == "initial_press":
                action = on if is_on() else off
                action()

        return handler

    for btn, onoff in zip(btns, actions):
        btn.handler(make_handler(*onoff))


@test
def wtf():
    from prototype3 import prototype

    class light(prototype):
        on = {"on": False}
        type = "light"

        def put(self, v):
            self.wtf = v

    light.put("aap")
    test.eq("aap", light["wtf"])
    test.eq("aap", light.wtf)


@test
async def set_some_buttons_up():
    import asyncio
    import bridge
    from prototype3 import prototype

    class button(prototype):
        def handler(self, h):
            self.handle = h

    b = bridge.bridge()
    btn1 = button()
    btn2 = button()
    btn3 = button()
    btn4 = button()
    b._byname = {
        "button:mytap:1": btn1,
        "button:mytap:2": btn2,
        "button:mytap:3": btn3,
        "button:mytap:4": btn4,
    }

    class light(prototype):
        on = {"on": False}
        color_temperature = {
            "mirek_schema": {"mirek_maximum": 500, "mirek_minimum": 150}
        }
        type = "light"

        def put(self, v):
            print(v)
            self.puts = v

    mysceneII = prototype()
    mysceneIII = prototype()
    mysceneIV = prototype()

    class myccyle(prototype):
        def cct_brightness(self):
            return 3000, 70

    setup2(b, "button:mytap", light, myccyle, mysceneII, mysceneIII, mysceneIV)
    btn1.handle(prototype(button_report={"event": "initial_press"}))
    await asyncio.sleep(0)
    # test.eq({'on': {'on': True}}, light.puts)
