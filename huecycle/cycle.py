#!/usr/bin/env python
from sys import stdout
from time import sleep
from datetime import datetime, time


def loop(light):
    from itertools import izip
    from phase import phase, sinus, charge, constant
    from sunphase import get_ct_phase, rise_and_set, MIREK
    last_bri = last_ct = 0
    sun = rise_and_set(52.053055, 5.638889, -6.0)
    t_wake = time(7,15)
    t_sleep = time(22,15)
    while True:
        t_rise, t_set = sun.next()
        t_now = datetime.now().time()
        ct_phase = get_ct_phase(t_wake, t_sleep, t_rise, t_set, t_now)
        if t_wake <= t_now < t_sleep:
            bri_phase = phase(t_wake, t_sleep, sinus(charge(3.)), 0, 255)
        else:
            bri_phase = phase(t_sleep, t_wake, constant(0), 0, 0)
        for color_temp, brightness in izip(ct_phase, bri_phase):
            if color_temp != last_ct or brightness != last_bri:
                last_bri = brightness
                last_ct = color_temp
                print "%s; %dK; %.1f%%" % (datetime.now().strftime("%a %H:%M:%S"), MIREK/color_temp, brightness/2.55)
            light.send(dict(ct=color_temp, bri=brightness, on=True))
            stdout.flush()
            sleep(1.0)
        sleep(1.0)


if __name__ == "__main__":
    from misc import lamp, attenuator
    from config import LOCAL_HUE_API
    from extended_cct import extend_cct
    lamp = lamp(LOCAL_HUE_API + "groups/0/action")
    #lamp = lamp(LOCAL_HUE_API + "lights/1/state")
    lights = extend_cct(attenuator(lamp))
    #weather1 = weather("http://api.wunderground.com/api/%s/conditions/q/pws:IUTRECHT57.json" % WUNDERGROUND_API_KEY)
    try:
        loop(lights)
    except:
        from traceback import print_exc
        print_exc()
        sleep(60)

