from functools import partial
from controllers import cycle_cct, light_off, light_on, dim, scene_on

def setup(light, cycle, onoff, dim_down=None, reset=None, dim_up=None):
    """
        Set up a tap with button:
        1 as on/off, given a CCT/dim cyle,
        2 and 4 as dim up/down and
        3 as reset to cycle.
    """

    @onoff.handler
    def handle(_, event):
        if light.on.on:
            light_off(light)
        else:
            cycle_cct(light, cycle)

    if dim_down:
        @dim_down.handler
        def handle(_, event):
            dim(light, delta=-25)

    if reset:
        @reset.handler
        def handle(_, event):
            cycle_cct(light, cycle)

    if dim_up:
        @dim_up.handler
        def handle(_, event):
            dim(light, delta=+25)



def setup2(bridge, name, light, cycle, sceneII, sceneIII, sceneIV):
    """
        Set up a tap with button:
        1 as on/off, given a CCT/dim cyle,
        2 and 4 as dim up/down and
        3 as reset to cycle.
    """
    onoff, dim_down, reset, dim_up = buttons(bridge.byname, name)
    last_scene = None

    @onoff.handler
    def handle(_, event):
        nonlocal last_scene
        if light.on.on:
            light_off(light)
        else:
            cycle_cct(light, cycle)
            last_scene = None

    @dim_down.handler
    def handle(_, event):
        nonlocal last_scene
        if light.on.on:
            dim(light, delta=-25)
        else:
            scene_on(sceneII)
            last_scene = sceneII

    @reset.handler
    def handle(_, event):
        nonlocal last_scene
        if light.on.on:
            if last_scene:
                scene_on(last_scene)
            else:
                cycle_cct(light, cycle)
        else:
            scene_on(sceneIII)
            last_scene = sceneIII

    @dim_up.handler
    def handle(_, event):
        nonlocal last_scene
        if light.on.on:
            dim(light, delta=+25)
        else:
            scene_on(sceneIV)
            last_scene = sceneIV


def buttons(byname, name, n=4):
    return [byname(f'{name}:{i}') for i in range(1, 1 + n)]


def setup4(bridge, name, light, *actions):
    n = len(actions)
    btns = buttons(bridge.byname, name, n)
    def make_handler(on, off):
        def handler(service, event):
            if event.button_report.event == 'initial_press':
                action = on if light.on.on else off
                action()
        return handler
    for btn, onoff in zip(btns, actions):
        btn.handler(make_handler(*onoff))


def setup5(device, is_on, *actions):
    n = len(actions)
    name = device.qname.split(':')[-1]
    print("NAME:", name)
    btns = [device.byname(f'button:{name}:{i}') for i in range(1, 1 + n)]
    def make_handler(on, off):
        def handler(service, event):
            if event.button_report.event == 'initial_press':
                action = on if is_on() else off
                action()
        return handler
    for btn, onoff in zip(btns, actions):
        btn.handler(make_handler(*onoff))
    

