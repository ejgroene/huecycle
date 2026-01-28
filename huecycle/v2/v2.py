import asyncio
import cct_cycle
import location
import datetime

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s')

from observable import Observable
from bridge import Bridge
from extended_cct import MIREK
from utils import sleep, clamp, logexceptions


t_wake = datetime.time(hour=7)
t_sleep = datetime.time(hour=23)

# Natural daylight cycle
my_cycle = cct_cycle.cct_cycle(
        location.location('52:01.224', '5:41.065'),
        t_wake=t_wake, t_sleep=t_sleep)


class Circadian(Observable):
    # Controls lights permanently to follow brightness and CCT from the sun.

    def __init__(self):
        self.task = None            # background task/loop
        self.dim = 1                # relative impact of brightness: 100%
        self.hue = 1                # relative impact of CCT: 100%
        self.on = None              # start with unknown 'on' state
        self.force = False          # override others (apps) settings
        self.taking_control = False # taking over control from app in progress
        self.extra = {}             # support extra attributes from observees
        super().__init__()

    def init(self):
        self.task = asyncio.create_task(self.loop())

    async def loop(self):
        while True:
            with logexceptions():
                match self.on:

                    case None:
                        await sleep(500)

                    case False: #TODO not repeat sending off
                        msg = {'on': {'on': False}}
                        msg.update(self.extra)
                        self.send(msg, force=self.force)
                        self.extra = {}
                        self.force = False
                        await sleep(500)

                    case True:
                        update = {'on': {'on': True}}
                        last_cct = last_bri = None
                        while self.on:
                            cct, bri = my_cycle.cct_brightness()
                            bri = clamp(bri * self.dim, my_cycle.br_dim, my_cycle.br_max)
                            cct = clamp(cct * self.hue, my_cycle.cct_min, my_cycle.cct_sun)
                            if self.force:
                                update['on'] = {'on': True}
                            if bri != last_bri or self.force:
                                update['dimming'] = {'brightness': bri}
                                last_bri = bri
                            if cct != last_cct or self.force:
                                update['color_temperature'] = {'mirek': MIREK // cct}
                                last_cct = cct
                            if update:
                                update.update(self.extra)
                                self.extra = {}
                                self.send(update, force=self.force)
                                self.force = False
                                update = {}
                            await sleep(60)

    def proceed(self, **attrs):        # sets attributes and notifies event loop
        self.on_by_motion = False      # only turn off by non-motion when turned on by motion
        for k, v in attrs.items():     # set the given attributes 
            setattr(self, k, v)
        self.task.cancel()             # wake up the loop

    def button(self, button, **kwargs):
        if button['button_report']['event'] == 'initial_press':  # normal toggle, respect external controllers
            self.proceed(on=not self.on)
        elif button['button_report']['event'] == 'long_press':   # force and take control
            self.force_control(button)

    def toggle_lights(self, button, **_):
        self.proceed(on=not self.on)

    def dim_lights(self, button, **_):
        self.proceed(dim=self.dim / 1.25, hue=self.hue / 1.25)

    def brighten_lights(self, button, **_):
        self.proceed(dim=self.dim * 1.25, hue=self.hue * 1.25)

    def force_control(self, button, **_):
        self.proceed(dim=1, hue=1, on=True, force=True)

    def scene(self, status=None, scene=None):
        # 'scene' only has a value when we rewrite the scene's actions

        if status: # someone in the app activated the 'Circadian' scene

            if status.get('active') == 'static':
                # scene activated: taking over control step 1
                self.proceed(dim=1, hue=1, on=True, force=True, taking_control=True)

            if self.taking_control and status.get('active') == 'inactive':
                # scene gets deactivated by our actions
                self.proceed(dim=1, hue=1, on=True, force=True, taking_control=False)


    def motion(self, motion, **kwargs):
        if not self.on and motion['motion'] == True:
            self.proceed(on=True, on_by_motion=True)
        elif self.on and self.on_by_motion and motion['motion'] == False:
            self.proceed(on=False)


    def unknown(self, msg):
        # handles message from Twilighttimer (thinks we're a light)
        # it sends on/off with duration.
        if 'on' in msg:
            self.proceed(on=msg['on']['on'], extra=msg)


class Twilighttimer(Observable):
    # Turns light on at early morning, off at dusk, on at dawn and off at bedtime

    def __init__(self, low, high, early, bedtime):
        self.low = low
        self.high = high
        self.early = early
        self.bedtime = bedtime
        self.avg_light_level = (high + low) // 2
        self.samples = [self.avg_light_level] * 5
        self.on = None
        super().__init__()

    async def loop(self):
        while True:
            with logexceptions():
                now = datetime.datetime.now().time()

                logging.info(f"SCHEMER: {self.early}, {self.bedtime}, {self.avg_light_level}, {self.on}")

                if now < self.early:
                    pass

                elif self.early < now < self.bedtime:

                    if self.avg_light_level < self.low:
                        # we send only once, leave user in control
                        if self.on != True:
                            self.send({'on': {'on': True}, 'dynamics': {'duration': 5000}})
                            self.on = True

                    elif self.avg_light_level > self.high:
                        if self.on != False:
                            self.send({'on': {'on': False}, 'dynamics': {'duration': 5000}})
                            self.on = False

                elif now > self.bedtime:
                    if self.on != False:
                        self.send({'on': {'on': False}, 'dynamics': {'duration': 5000}})
                        self.on = False

                await sleep(300)

    def light_level(self, light, **kwargs):
        self.samples.append(light['light_level'])
        self.samples.pop(0)
        self.avg_light_level = sum(self.samples) // len(self.samples)
        self.task.cancel()

    def init(self):
        self.task = asyncio.create_task(self.loop())



bridge = Bridge('https://192.168.178.78/', "IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt")
device = bridge.device


kantoor_cycle = (Circadian(),
                    (device('Bolt Chandelier 1'),),
                    (device('Bolt Chandelier 2'),),
                    (device('Bolt Chandelier 3'),),
                    (device('Bolt Chandelier 4'),),
                    (device('Bolt Chandelier 5'),),
                    (device('Bolt Chandelier 6'),),
                )

events = bridge.configure(
    (device('Kantoor knopje', 1),
        kantoor_cycle,
    ),
    (device('Sensor Kantoor', 'motion'),
        kantoor_cycle,
    ),
    (device('Kantoor Tap', 1, button='toggle_lights'),
        kantoor_cycle,
    ),
    (device('Kantoor Tap', 2, button='dim_lights'),
        kantoor_cycle,
    ),
    (device('Kantoor Tap', 3, button='force_control'),
        kantoor_cycle,
    ),
    (device('Kantoor Tap', 4, button='brighten_lights'),
        kantoor_cycle,
    ),
    (device('Kantoor', 'Circadian'),
       kantoor_cycle,
    ),
    (device('Sensor Kantoor', 'light_level'),
        (Twilighttimer(15000, 20000, t_wake, t_sleep),
            (Circadian(),
                (device('Tolomeo'),),
            ),
        ),
    ),
)

# IDEA: write emtpty actions or noop into all 'Cirdadian' scene's
import pprint
c = device('Kantoor', 'Circadian')
""" inhoud van een 'scene':
{'actions': [{'action': {'color_temperature': {'mirek': 223},
                         'dimming': {'brightness': 50.2},
                         'on': {'on': True}},
              'target': {'rid': 'f7375d8a-194e-48ce-99bb-56ff89a770a6',
                         'rtype': 'light'}},
"""
actions = c._data['actions']
# we set the scene top no-op (more or less, only on=on remains, which doesn't do anything)
# Circadian could also detect all 'Circadian' scenes and do this and include them automatically.
# Circadian's loop could also update the scene with bri/cct and then activate the scene... (nice!)
#   that would interfere a bit with the indivdual controlling of lights
#   but would reduce PUTs and make transitions happen all at once
for action in actions:
    action['action'] = {'on': {'on': True}}
c.receive({'actions': actions})
asyncio.run(events(), debug=True)

