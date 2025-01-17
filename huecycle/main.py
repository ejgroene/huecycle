import asyncio
import datetime
import bridge
import utils
import tap
import timers
import pprint
import traceback
from datetime import timedelta
from cct_cycle import cct_cycle, location
from controllers import cycle_cct, light_off, light_on, dim, randomize, on_motion
from twilight import twilight

""" IDEAs
    1. When a scena called 'Automatic' is activated (by the app)
       put the light/group on cct_cycle.
"""

# Personal bridge, on my network and with my key
my_bridge = bridge.bridge(
    baseurl="https://192.168.178.78",
    username="IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt",  # hue-application-key,
)

# My location on Earth
my_location = location("52:01.224", "5:41.065")


# Read data from Hue bridge and print its devices for reference
my_bridge.read_objects()
utils.print_overview(my_bridge)

# Keep byname lookup method, it's handy
byname = my_bridge.byname


##### Algemeen #####
algemeen_cycle = cct_cycle(
    loc=my_location, t_wake=datetime.time(hour=7), t_sleep=datetime.time(hour=23)
)


warm_cycle = algemeen_cycle(cct_moon=2200, cct_sun=4000)
koud_cycle = algemeen_cycle(cct_moon=10000)


##### Kantoor #####
kantoor_cycle = koud_cycle()
kantoor_groep = byname("grouped_light:Kantoor")
kantoor_motion = byname("motion:Sensor Kantoor")
kantoor_button = byname("button:Kantoor knopje:1")


enable_sensor = lambda: on_motion(
    kantoor_motion,
    lambda: cycle_cct(kantoor_groep, kantoor_cycle),
    lambda: light_off(kantoor_groep, after=5 * 60),
)
enable_sensor()


@kantoor_button.handler
def handle(button, event):
    if event["last_event"] == "initial_press":
        if kantoor_groep.on.on:
            light_off(kantoor_groep)
        else:
            cycle_cct(kantoor_groep, kantoor_cycle)


##### Entree #####
entree_cycle = warm_cycle(br_dim=40)
entree_motion = byname("motion:Sensor Entree")
entree_groep = byname("grouped_light:Entree")
entree_lightlevel = byname("light_level:Sensor Entree")


on_motion(
    entree_motion,
    lambda: cycle_cct(entree_groep, entree_cycle),
    lambda: light_off(entree_groep, after=2 * 60, duration=5000),
)


##### Keuken #####
keuken_cycle = warm_cycle(br_min=10, br_max=60)
keuken_aanrecht = byname("light:Keuken Aanrecht")
staande_schemer = byname("light:Staande Schemerlamp")
keuken_scene_II = byname("scene:room:Keuken:Tap:II")
keuken_scene_III = byname("scene:room:Keuken:Tap:III")
keuken_scene_IV = byname("scene:room:Keuken:Tap:IV")

keuken_aanrecht_on = lambda: cycle_cct(keuken_aanrecht, keuken_cycle)
keuken_aanrecht_off = lambda: light_off(keuken_aanrecht)
keuken_aanrecht_dim = lambda: dim(keuken_aanrecht, delta=-25)
keuken_aanrecht_brighten = lambda: dim(keuken_aanrecht, delta=+25)

staande_schemer_on = lambda: cycle_cct(staande_schemer, keuken_cycle)
staande_schemer_off = lambda: light_off(staande_schemer)
staande_schemer_dim = lambda: dim(staande_schemer, delta=-25)
staande_schemer_brighten = lambda: dim(staande_schemer, delta=+25)

keuken_on = lambda: [keuken_aanrecht_on(), staande_schemer_on()]
keuken_off = lambda: [keuken_aanrecht_off(), staande_schemer_off()]

# set up dimmer switch aanrecht
tap.setup4(
    my_bridge,
    "button:Aanrecht Dimmer",
    keuken_aanrecht,
    (keuken_aanrecht_on, keuken_aanrecht_on),
    (utils.noop, keuken_aanrecht_brighten),
    (utils.noop, keuken_aanrecht_dim),
    (utils.noop, keuken_aanrecht_off),
)


#### Keuken/Woonkamer


##### Woonkamer #####
woonkamer_cycle = warm_cycle(br_max=70)
woonkamer_groep = byname('grouped_light:Woonkamer')
woonkamer_on = lambda: cycle_cct(woonkamer_groep, woonkamer_cycle)
woonkamer_off = lambda: light_off(woonkamer_groep)
woonkamer_brighten = lambda: dim(woonkamer_groep, delta=+25)
woonkamer_dim = lambda: dim(woonkamer_groep, delta=-25)


# set up tap op de paal
tap.setup4(
    my_bridge,
    "button:Keuken Tap",
    staande_schemer,
    (lambda: [staande_schemer_on(), woonkamer_on()], lambda: [staande_schemer_off(), woonkamer_off()]),
    (utils.noop, lambda: [staande_schemer_dim(), woonkamer_dim()]),
    (utils.noop, lambda: [staande_schemer_on(), woonkamer_on()]),
    (utils.noop, lambda: [staande_schemer_brighten(), woonkamer_brighten()]),
)
    
    

##### Badkamer #####
badkamer_groep = byname("grouped_light:Badkamer")
badkamer_scene_II = byname("scene:room:Badkamer:Tap:II")
badkamer_scene_III = byname("scene:room:Badkamer:Tap:III")
badkamer_scene_IV = byname("scene:room:Badkamer:Tap:IV")
badkamer_cycle = warm_cycle()
tap.setup2(
    my_bridge,
    "button:Badkamer Tap",
    badkamer_groep,
    badkamer_cycle,
    badkamer_scene_II,
    badkamer_scene_III,
    badkamer_scene_IV,
)


##### Overloop #####
overloop_cycle = warm_cycle(br_dim=1, cct_min=1667)
overloop_nok = byname("light:Overloop Nok")
overloop_on = lambda: cycle_cct(overloop_nok, overloop_cycle)
overloop_off = lambda: light_off(overloop_nok)


tap.setup4(
    my_bridge,
    "button:Overloop Tap",
    overloop_nok,
    (overloop_on, overloop_off),
    (utils.noop, lambda: dim(overloop_nok, delta=-25)),
    (utils.noop, overloop_on),
    (utils.noop, lambda: dim(overloop_nok, delta=+25)),
)



##### Algemeen (timers) #####
twilight_on = lambda: randomize(
    timedelta(minutes=10), keuken_on, overloop_on, woonkamer_on
)
twilight_off = lambda: randomize(
    timedelta(minutes=10), keuken_off, overloop_off, woonkamer_off
)
is_twilight = twilight(
    entree_lightlevel, on_dawn=twilight_off, on_dusk=twilight_on, threshold=1000
)


async def main():
    timers.at_time_do(
        datetime.time(7, 00), lambda: twilight_on() if is_twilight() else None
    )
    timers.at_time_do(datetime.time(23, 00), twilight_off)
    while True:
        try:
            await my_bridge.dispatch_events()
        except KeyboardInterrupt:
            break
        except:
            traceback.print_exc()
            await asyncio.sleep(10)


##### Run bridge event dispatcher forever #####
asyncio.run(main(), debug=True)
