import asyncio
import datetime
import bridge
import utils
import tap
import timers
import pprint
from cct_cycle import cct_cycle, location
from controllers import cycle_cct, light_off, light_on, dim
from twilight import twilight

""" IDEAs
    1. When a scena called 'Automatic' is activated (by the app)
       put the light/group on cct_cycle.
"""

# Personal bridge, on my network and with my key
my_bridge = bridge.bridge(
    baseurl  = 'https://192.168.178.78',
    username = "IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt" # hue-application-key,
)

# My location on Earth
my_location = location("52:01.224", "5:41.065")


# Read data from Hue bridge and print its devices
my_bridge.read_objects()
utils.print_overview(my_bridge)

# Keep byname lookup method, it's handy
byname = my_bridge.byname


##### Algemeen #####
algemeen_cycle = cct_cycle(
          loc      = my_location,
          t_wake   = datetime.time(hour= 7),
          t_sleep  = datetime.time(hour=23))


##### Kantoor #####
kantoor_cycle = algemeen_cycle()

kantoor_groep      = byname('grouped_light:Kantoor')
kantoor_motion     = byname('motion:Sensor Kantoor')
kantoor_button     = byname('button:Kantoor knopje:1')

@kantoor_button.handler
def handle(button, event):
    press = event['last_event']
    if press == 'initial_press':
        cycle_cct(kantoor_groep, kantoor_cycle)
    elif press == 'long_press':
        light_off(kantoor_groep)

@kantoor_motion.handler
def handle(motion, event):
    if event.get('motion'):
        cycle_cct(kantoor_groep, kantoor_cycle)
    else:
        light_off(kantoor_groep, after=5*60)



##### Entree #####
entree_motion      = byname('motion:Sensor Entree')
entree_groep       = byname('grouped_light:Entree')
entree_lightlevel  = byname('light_level:Sensor Entree')

entree_cycle = algemeen_cycle(
          cct_min  = 2200,
          cct_sun  = 4000,
          cct_moon = 6500,
          br_dim   =   50)

@entree_motion.handler
def handle(motion, event):
    if event.get('motion'):
        cycle_cct(entree_groep, entree_cycle)
    else:
        light_off(entree_groep, after=2*60, duration=5000)



##### Keuken #####
keuken_cycle             = algemeen_cycle(br_max=60)
keuken_aanrecht          = byname('light:Keuken Aanrecht')
keuken_schemer           = byname('light:Keuken Schemerlamp')
keuken_scene_II          = byname('scene:room:Keuken:Tap:II')
keuken_scene_III         = byname('scene:room:Keuken:Tap:III')
keuken_scene_IV          = byname('scene:room:Keuken:Tap:IV')

keuken_aanrecht_on       = lambda: cycle_cct(keuken_aanrecht, keuken_cycle)
keuken_aanrecht_off      = lambda: light_off(keuken_aanrecht)
keuken_aanrecht_dim      = lambda: dim(keuken_aanrecht, delta=-25)
keuken_aanrecht_brighten = lambda: dim(keuken_aanrecht, delta=+25)

keuken_schemer_on        = lambda: cycle_cct(keuken_schemer, keuken_cycle)
keuken_schemer_off       = lambda: light_off(keuken_schemer)
keuken_schemer_dim       = lambda: dim(keuken_aanrecht, delta=-25)
keuken_schemer_brighten  = lambda: dim(keuken_aanrecht, delta=+25)

keuken_on                = lambda: [keuken_aanrecht_on(), keuken_schemer_on()]
keuken_off               = lambda: [keuken_aanrecht_off(), keuken_schemer_off()]

tap.setup2(my_bridge, 'button:Keuken Tap', keuken_schemer, keuken_cycle, keuken_scene_II, keuken_scene_III, keuken_scene_IV)

is_twilight = twilight(entree_lightlevel, keuken_off, keuken_on, threshold=4000) 

tap.setup4(my_bridge, 'button:Aanrecht Dimmer', keuken_aanrecht,
    (keuken_aanrecht_on      , keuken_aanrecht_on),
    (keuken_aanrecht_brighten, utils.noop),
    (keuken_aanrecht_dim     , utils.noop),
    (keuken_aanrecht_off     , utils.noop))

#keuken_aanrecht_dimmer = byname('device:Aanrecht Dimmer')
#tap.setup5(keuken_aanrecht_dimmer, lambda: keuken_aanrecht.on,
#    (keuken_aanrecht_on      , keuken_aanrecht_on),
#    (keuken_aanrecht_brighten, utils.noop),
#    (keuken_aanrecht_dim     , utils.noop),
#    (keuken_aanrecht_off     , utils.noop))



##### Badkamer #####
badkamer_groep     = byname('grouped_light:Badkamer')
badkamer_scene_II  = byname('scene:room:Badkamer:Tap:II')
badkamer_scene_III = byname('scene:room:Badkamer:Tap:III')
badkamer_scene_IV  = byname('scene:room:Badkamer:Tap:IV')
badkamer_cycle     = algemeen_cycle()
tap.setup2(my_bridge, 'button:Badkamer Tap', badkamer_groep, badkamer_cycle, badkamer_scene_II, badkamer_scene_III, badkamer_scene_IV)



##### Overloop #####
overloop_cycle  = algemeen_cycle(br_dim=1, cct_min=1667)
overloop_nok    = byname('light:Overloop Nok')

tap.setup4(my_bridge, 'button:Overloop Tap', overloop_nok,
    (lambda: light_off(overloop_nok), lambda: cycle_cct(overloop_nok, overloop_cycle)),
    (lambda: dim(overloop_nok, delta = -25), utils.noop),
    (lambda: cycle_cct(overloop_nok, overloop_cycle), utils.noop),
    (lambda: dim(overloop_nok, delta = +25), utils.noop))




##### Algemeen (timers) #####
async def main():
    cycle_cct(overloop_nok, overloop_cycle) # always turn on
    timers.at_time_do(datetime.time( 7,00), keuken_on if is_twilight() else None)
    timers.at_time_do(datetime.time(23,20), keuken_off)
    await my_bridge.dispatch_events()
    


##### Run bridge event dispatcher forever #####
asyncio.run(main(), debug=True)
