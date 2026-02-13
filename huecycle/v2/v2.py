import asyncio
import cct_cycle
import location
import datetime
import statistics

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s')

from controller import Controller
from bridge import Bridge
from extended_cct import MIREK
from utils import sleep, clamp, logexceptions, update


t_wake = datetime.time(hour=7)
t_sleep = datetime.time(hour=23)

# Natural daylight cycle
my_cycle = cct_cycle.cct_cycle(
        location.location('52:01.224', '5:41.065'),
        t_wake=t_wake, t_sleep=t_sleep)


class Circadian(Controller):
    # Controls lights permanently to follow brightness and CCT from the sun.

    def init(self):
        self.last_mirek = self.last_bri = self.last_on = None
        self.last_dim = self.last_hue = 1.0
        self.on_by_motion = None
        self.off_by_motion_timer = None
        self.start_message_dispatcher(self.handle_event, timeout_s=60)

    def handle_event(self, on=None, dim=None, hue=None, force=False, extra=()):
        # handles events from responders below and periodically updates cct and brightness
        if force:
            self.last_hue = self.last_dim = 1.0
        if dim:
            self.last_dim *= dim
        if hue:
            self.last_hue *= hue
        msg = dict(extra)

        if on is not None and on != self.last_on or force:
            update(msg, ('on', 'on'), on)
            self.last_bri = None # soft-force (re)send of brightness to avoid 'external control'
            self.last_on = on

        if self.last_on or force:
            cct, bri = my_cycle.cct_brightness()
            bri = clamp(bri * self.last_dim, my_cycle.br_dim, my_cycle.br_max)
            cct = clamp(cct * self.last_hue, my_cycle.cct_min, my_cycle.cct_sun)
            mirek = MIREK // cct
            # we send both, because if we only send mirek, we also get an
            # unsollicited brightness event, which we cannot tell ours (sometimes)
            if bri != self.last_bri or mirek != self.last_mirek or force:
                self.last_bri = bri
                self.last_mirek = mirek
                update(msg, ('dimming', 'brightness'), bri)
                update(msg, ('color_temperature', 'mirek'), mirek)

        if msg:
            self.send(msg, force=force)

    def button(self, button, **_):
        # responder for the 'smart' button
        event = button['button_report']['event']
        if  event == 'initial_press':
            self.toggle_lights()
        elif event == 'long_press':
            self.force_on()

    def toggle_lights(self, **_):
        # responder for the Tap 1 button
        self.cancel_motion_off()
        self.dispatch_message(on=not self.last_on)

    def dim_lights(self, **_):
        # responder for the Tap 2 button
        self.dispatch_message(on=True, dim=1/1.25, hue=1/1.25)

    def brighten_lights(self, **_):
        # responder for the Tap 4 button
        self.dispatch_message(on=True, dim=1.25, hue=1.25)

    def force_on(self, **_):
        # responder for the Tap 3 button
        self.cancel_motion_off()
        self.dispatch_message(on=True, force=True)

    def scene(self, status=None, scene=None):
        # responder for scene activation via app
        if status:
            active = status.get('active')
            if active == 'static':
                # scene activated: taking over control step 1
                self.taking_control = True
                self.force_on()
            if self.taking_control and active == 'inactive':
                # scene gets deactivated by our actions
                self.taking_control = False
                self.force_on()

    def cancel_motion_off(self):
        if self.off_by_motion_timer:
            self.off_by_motion_timer.cancel()
        self.off_by_motion_timer = None

    def motion(self, motion, **_):
        # responder for the motion sensor
        motion = motion['motion']
        if motion == True:
            self.cancel_motion_off()
            if self.last_on:
                return
            self.on_by_motion = True
            self.dispatch_message(on=True)
        elif motion == False and self.on_by_motion:
            self.cancel_motion_off()
            def motion_off():
                self.dispatch_message(on=False)
                self.on_by_motion = False
            self.off_by_motion_timer = asyncio.get_running_loop().call_later(60, motion_off)

    def on(self, on, **extra):
        # responder for 'on' message from Twilighttimer (thinks we're a light)
        self.dispatch_message(on=on['on'], extra=extra)


class Twilighttimer(Controller):
    # Turns light on at early morning, off at dusk, on at dawn and off at bedtime

    def __init__(self, low, high, early, bedtime):
        self.low = low
        self.high = high
        self.early = early
        self.bedtime = bedtime
        self.samples = []
        self.on = None  # not on and not off
        super().__init__()

    def init(self):
        self.start_message_dispatcher(self.handle_event, timeout_s=30)

    def handle_event(self, avg_light_level=None):
        now = datetime.datetime.now().time()
        logging.info(f"SCHEMER: {self.early}, {self.bedtime}, {avg_light_level}, {self.on}")

        if now < self.early:
            pass

        elif self.early < now < self.bedtime:

            if avg_light_level and avg_light_level < self.low:
                # we send only once, leave user in control
                if self.on != True:
                    self.send({'type': 'on', 'on': {'on': True}}) #, 'dynamics': {'duration': 5000}})
                    self.on = True

            elif avg_light_level and avg_light_level > self.high:
                if self.on != False:
                    self.send({'type': 'on', 'on': {'on': False}}) #, 'dynamics': {'duration': 5000}})
                    self.on = False

        elif now > self.bedtime:
            if self.on != False:
                self.send({'type': 'on', 'on': {'on': False}}) #, 'dynamics': {'duration': 5000}})
                self.on = False


    def light_level(self, light, **kwargs):
        self.samples.append(light['light_level'])
        if len(self.samples) > 2:
            self.dispatch_message(avg_light_level=int(statistics.mean(self.samples)))
            self.samples.pop(0)



bridge = Bridge('https://192.168.178.78/', "IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt")
device = bridge.device


bolt_cycle =    (Circadian('Bolt'),
                    (device('Bolt Chandelier 1'),),
                    (device('Bolt Chandelier 2'),),
                    (device('Bolt Chandelier 3'),),
                    (device('Bolt Chandelier 4'),),
                    (device('Bolt Chandelier 5'),),
                    (device('Bolt Chandelier 6'),),
                )

tolomeo_cycle = (Circadian('Tolomeo'),
                    (device('Tolomeo'),),
                )


events = bridge.configure(
    (device('Kantoor knopje', 1),
        bolt_cycle,
        #tolomeo_cycle,
    ),
    (device('Kantoor Tap', 1, button='toggle_lights'),
        bolt_cycle,
        tolomeo_cycle,
    ),
    (device('Kantoor Tap', 2, button='dim_lights'),
        bolt_cycle,
        tolomeo_cycle,
    ),
    (device('Kantoor Tap', 3, button='force_on'),
        bolt_cycle,
        tolomeo_cycle,
    ),
    (device('Kantoor Tap', 4, button='brighten_lights'),
        bolt_cycle,
        tolomeo_cycle,
    ),
    (device('Kantoor', 'Circadian'),
        bolt_cycle,
        tolomeo_cycle,
    ),
    (device('Sensor Kantoor', 'motion'),
        bolt_cycle,
        tolomeo_cycle,
    ),
    (device('Sensor Kantoor', 'light_level'),
        (Twilighttimer(20000, 25000, t_wake, t_sleep),
            tolomeo_cycle,
        ),
    ),
    (device('Sensor Entree', 'motion'),
        (Circadian('Entree'),
            (device('Entree',),),
        ),
    ),
)

asyncio.run(events(), debug=True)

