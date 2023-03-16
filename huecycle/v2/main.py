import time
import datetime
import zoneinfo
import bridge
import utils
import extended_cct
from cct_cycle import cct_cycle, location
from controllers import cycle_cct, light_off, light_on

import logging
logging.captureWarnings(True) # get rid of unverified https certificate
logging.basicConfig(level=logging.ERROR)

import autotest
test = autotest.get_tester(__name__)


b = bridge.bridge(
    baseurl='https://192.168.178.78',
    username="IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt" # hue-application-key,
)

async def main():
    await b.read_objects()
    byname = b.byname()
    utils.print_overview(b)

    ams   = zoneinfo.ZoneInfo('Europe/Amsterdam')
    cycle = cct_cycle(
                loc      = location("52:01.224", "5:41.065"),
                t_wake   = datetime.time(hour= 7, tzinfo=ams),
                t_sleep  = datetime.time(hour=23, tzinfo=ams))


    office = byname['grouped_light:Office']
    motion = byname['motion:Hue motion sensor 1']
    lightl = byname['light_level:Hue motion sensor 1']
    button = byname['button:Buro Dumb Button']


    # IDEA: let event be an awaitable, so you can write loops that maintain state:
    #@button.loop_handler
    async def loop(button, event):
        last = None
        while True:
            e = await event
            if e.aap and last.noot:
                do_A()
            else:
                do_B()
            last = e


    @button.handler
    def handle(button, event):
        press = event['last_event']
        if press == 'initial_press':
            #if office.on.on:
            #    increase_brightness(cycle)
            cycle_cct(office, cycle)
        elif press == 'long_press':
            light_off(office)


    @motion.handler
    def handle(motion, event):
        if event.get('motion'):
            cycle_cct(office, cycle)
        else:
            """ TODO cancels cycle_cct, which is problematic:
                cct and brightness control stops; if a motion
                event comes which reinstalls cycle_cct, the
                CCT and brightness will suddenly shift a bit
                to update from the time it hasn't updated.
            """
            light_off(office, after=5*60)


    # IDEA
    def increase_brightness(cycle):
        print("increasing brightness")
        cycle.br_dim *= 1.5
        cycle.br_max *= 1.5

    def decrease_brightness(cycle):
        cycle.br_dim /= 1.5
        cycle.br_max /= 1.5

        
    async for service, update in b.eventstream():
        print(f"{service.qname!r}: {dict(update)}")
        if hasattr(service, 'event_handler'):
            service.event_handler(update)
            continue
        """ update internal state to reflect changes """
        old = service.keys()
        service.update(update)
        diff = old ^ service.keys()
        assert diff <= {'temperature_valid'}, diff
        await asyncio.sleep(0)


import asyncio
asyncio.run(main(), debug=True)
