import asyncio
import datetime
import bridge
import utils
import tap
import pprint
from cct_cycle import cct_cycle, location
from controllers import cycle_cct, light_off, light_on, dim


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



##### Kantoor #####
kantoor_cycle = cct_cycle(
          loc      = my_location,
          t_wake   = datetime.time(hour= 7),
          t_sleep  = datetime.time(hour=23))

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

entree_cycle = kantoor_cycle(
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
keuken_groep      = byname('grouped_light:Keuken')
keuken_scene_II   = byname('scene:room:Keuken:Tap:II')
keuken_scene_III  = byname('scene:room:Keuken:Tap:III')
keuken_scene_IV   = byname('scene:room:Keuken:Tap:IV')

woon_cycle        = kantoor_cycle()

tap.setup2(my_bridge, 'button:Keuken Tap', keuken_groep, woon_cycle, keuken_scene_II, keuken_scene_III, keuken_scene_IV)




##### Run bridge event dispatcher forever #####
asyncio.run(my_bridge.dispatch_events(), debug=True)
