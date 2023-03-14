import time
import datetime
import zoneinfo
import bridge
import utils
import cct_cycle
import extended_cct
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
    cycle = cct_cycle.cct_cycle(
            lat      = "52:01.224",
            lon      =  "5:41.065",
            t_wake   = datetime.time(hour= 7, tzinfo=ams),
            t_sleep  = datetime.time(hour=23, tzinfo=ams),
            cct_min  =  2000,
            cct_sun  =  5000,
            cct_moon = 10000,
            br_dim   =    10,
            br_max   =   100)


    office = byname['grouped_light:Office']
    motion = byname['motion:Hue motion sensor 1']
    lightl = byname['light_level:Hue motion sensor 1']
    button = byname['button:Buro Dumb Button']

    # TODO
    def handle(button, update):
        pass
    button.handler = handle


    t_now = 0
    press = None        
    async for service, update in b.eventstream():          # TODO make non-blocking
        cct, brightness = cycle.cct_brightness()
        print(f"{service.qname!r}: {dict(update)}")
        t_last = t_now
        t_now = time.monotonic()
        if service == button:

            # TODO how to make double press detection easy
            last_press = press
            press = update['last_event']
            if press == 'initial_press':
                if last_press == 'short_release' and t_now - t_last < 1:

                    light_on(office, brightness=100, ct=3000)
                else:
                    cycle_cct(office, cycle)
            elif press == 'long_press':
                light_off(office)
        elif service == motion:
            if update.get('motion'): # could also be 'sensitivity'
                if not office.on.on:
                    cycle_cct(office, cycle)
                    light_off(after=5*60) # cancels cycle_cct immediately...
        else:
            """ update internal state to reflect changes """
            old = service.keys()
            service.update(update)
            diff = old ^ service.keys()
            assert diff <= {'temperature_valid'}, diff

        await asyncio.sleep(0)
            

import asyncio
asyncio.run(main())
