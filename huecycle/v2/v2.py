import asyncio
import logging
import cct_cycle
import location
import datetime
import time
import itertools

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s')

from observable import Observable
from bridge import Bridge
from extended_cct import MIREK
from utils import sleep, clamp, Adapt, logexceptions


my_location = location.location('52:01.224', '5:41.065')

t_wake=datetime.time(hour=7)
t_sleep=datetime.time(hour=23)

my_cycle = cct_cycle.cct_cycle(
        my_location,
        t_wake=t_wake,
        t_sleep=t_sleep,
        )

class Circadian(Observable):

    def __init__(self):
        self.task = None
        self.dim = 1
        self.hue = 1
        self.on = None
        self.force = False
        self.taking_control = False
        super().__init__()

    def init(self):
        self.task = asyncio.create_task(self.loop())

    async def loop(self):
        while True:
            with logexceptions():
                match self.on:

                    case None:
                        await sleep(500)

                    case False:
                        self.send({'on': {'on': False}}, force=self.force)
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
                                self.send(update, force=self.force)
                                self.force = False
                                update = {}
                            await sleep(60)

    def proceed(self, **kw):
        self.on_by_motion = False
        for k, v in kw.items():
            setattr(self, k, v)
        self.task.cancel()

    def button(self, button, **kwargs):
        if button['button_report']['event'] == 'initial_press':
            self.proceed(on=not self.on)
        elif button['button_report']['event'] == 'long_press':
            self.tap3(None) # reset

    def motion(self, motion, **kwargs):
        if self.on and self.on_by_motion and motion['motion'] == False:
            self.proceed(on=False)
        if not self.on and motion['motion'] == True:
            self.proceed(on=True, on_by_motion=True)

    def tap1(self, button, **kwargs):
        self.proceed(on=not self.on)

    def tap2(self, button, **kwargs):
        self.proceed(dim=self.dim / 1.25, hue=self.hue / 1.25)

    def tap3(self, button, **kwargs):
        self.proceed(dim=1, hue=1, on=True, force=True)

    def tap4(self, button, **kwargs):
        self.proceed(dim=self.dim * 1.25, hue=self.hue * 1.25)

    def scene(self, status):
        logging.info(f"SCENE: {status}")
        # taking over control by forcing messages
        if status.get('active') == 'static':
            self.proceed(dim=1, hue=1, on=True, force=True, taking_control=True)
        # after the scene-related events are processed, retake control
        if self.taking_control and status.get('active') == 'inactive':
            self.proceed(dim=1, hue=1, on=True, force=True, taking_control=False)

    def unknown(self, msg):
        if 'on' in msg:
            self.proceed(**msg['on'])
        else:
            logging.info(f"??? {self}: {msg}")


class Schemertimer(Observable):

    def __init__(self, lo, hi, from_, until):
        self.lo = lo
        self.hi = hi
        self.from_ = from_
        self.until = until
        self.noon  = datetime.time(12)
        self.midnight = datetime.time(23,59,59)
        self.samples = [(hi-lo)/2] * 5
        self.on = False
        self.avg = 0
        super().__init__()

    async def light_off(self):
        while True:
            with logexceptions():
                now = datetime.datetime.now().time()

                # ochtend
                if self.from_ < now < self.noon and self.avg < self.lo and self.on:
                    self.send({'on': {'on': False}})
                    self.on = False

                # avond
                if self.noon < now < self.until and self.avg > self.lo and not self.on:
                    self.send({'on': {'on': True}})
                    self.on = True

                # nacht
                if not self.from_ < now < self.until and self.on:
                    self.send({'on': {'on': False}})
                    self.on = False

                await sleep(300)

    def light_level(self, light, **kwargs):
        l = light['light_level']
        self.samples.append(l)
        self.samples.pop(0)
        self.avg = sum(self.samples) / len(self.samples)
        logging.info(f"SCHEMER: {l}, {int(self.avg)}, {self.lo}, {self.hi}")

    def init(self):
        asyncio.create_task(self.light_off())



#bridge = Bridge('https://ecb5fafffea7279d', "IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt")
bridge = Bridge('https://192.168.178.78/', "IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt")
device = bridge.device


kantoor_cycle = (Circadian(),
                    (device('Tolomeo'),),
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
    (device('Sensor Kantoor', 'light_level'),
        (Schemertimer(10000, 20000, t_wake, t_sleep),
            kantoor_cycle,
        ),
    ),
    (device('Kantoor Tap', 1, button='tap1'),
        (Adapt(button='tap1'),
            kantoor_cycle,
        ),
    ),
    (device('Kantoor Tap', 2),
        (Adapt(button='tap2'),
            kantoor_cycle,
        ),
    ),
    (device('Kantoor Tap', 3),
        (Adapt(button='tap3'),
            kantoor_cycle,
        ),
    ),
    (device('Kantoor Tap', 4),
        (Adapt(button='tap4'),
            kantoor_cycle,
        ),
    ),
    (device('Kantoor', 'Circadian'),
       kantoor_cycle,
    ),
)

asyncio.run(events(), debug=True)

