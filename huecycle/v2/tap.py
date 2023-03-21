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


def buttons(byname, name):
    return (byname(f'{name}:{n}') for n in (1,2,3,4))
