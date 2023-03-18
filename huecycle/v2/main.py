import time
import datetime
import zoneinfo
import bridge
import utils
import extended_cct
from cct_cycle import cct_cycle, location
from controllers import cycle_cct, light_off, light_on, dim

import logging
logging.captureWarnings(True) # get rid of unverified https certificate
logging.basicConfig(level=logging.ERROR)

import autotest
test = autotest.get_tester(__name__)


bridge_2 = bridge.bridge(
    baseurl='https://192.168.178.78',
    username="IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt" # hue-application-key,
)
bridge_2.read_objects()


async def main():
    byname = bridge_2.byname()
    utils.print_overview(bridge_2)

    ams   = zoneinfo.ZoneInfo('Europe/Amsterdam')

    kantoor_cycle = cct_cycle(
                loc      = location("52:01.224", "5:41.065"),
                t_wake   = datetime.time(hour= 7, tzinfo=ams),
                t_sleep  = datetime.time(hour=23, tzinfo=ams))

    entree_cycle = kantoor_cycle(
                cct_min=2200,
                cct_sun=4000,
                cct_moon=6500,
                br_dim=50)


    kantoor_groep      = byname['grouped_light:Office']
    kantoor_motion     = byname['motion:Sensor Kantoor']
    kantoor_lightlevel = byname['light_level:Sensor Kantoor']
    kantoor_button     = byname['button:Buro Dumb Button:1']

    entree_motion     = byname['motion:Sensor Entree']
    entree_lightlevel = byname['light_level:Sensor Entree']
    entree_groep      = byname['grouped_light:Entree']

    kantoor_tap_big       = byname['button:Hue tap switch 1:1']
    kantoor_tap_left      = byname['button:Hue tap switch 1:2']
    kantoor_tap_down      = byname['button:Hue tap switch 1:3']
    kantoor_tap_right     = byname['button:Hue tap switch 1:4']


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
            """ TODO cancels cycle_cct, which is problematic:
                cct and brightness control stops; if a motion
                event comes which reinstalls cycle_cct, the
                CCT and brightness will suddenly shift a bit
                to update from the time it hasn't updated.
            """
            light_off(kantoor_groep, after=5*60)


    @entree_motion.handler
    def handle(motion, event):
        if event.get('motion'):
            cycle_cct(entree_groep, entree_cycle, use_extended_cct=False)
        else:
            light_off(entree_groep, after=2*60, duration=5000)


    @kantoor_tap_big.handler
    def handle(tap, event):
        if kantoor_groep.on.on:
            light_off(kantoor_groep)
        else:
            cycle_cct(kantoor_groep, kantoor_cycle)


    @kantoor_tap_right.handler
    def handle(tap, event):
        dim(kantoor_groep, delta=+25)


    @kantoor_tap_down.handler
    def handle(tap, event):
        cycle_cct(kantoor_groep, kantoor_cycle)


    @kantoor_tap_left.handler
    def handle(tap, event):
        dim(kantoor_groep, delta=-25)


    async for service, update in bridge_2.eventstream():
        print(f"{service.qname!r}: {dict(update)}")
        if service.event_handler:
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
