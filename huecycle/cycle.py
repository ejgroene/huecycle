#!/usr/bin/env python
from sys import stdout, argv
from time import sleep
from datetime import datetime, time
from tap import tap


def loop(light, tap, bri_phase_map):
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
            bri_phase = phase(t_wake, t_sleep, bri_phase_map, 0, 255)
        else:
            bri_phase = phase(t_sleep, t_wake, constant(0), 0, 0)
        for color_temp, brightness in izip(ct_phase, bri_phase):
            s = tap.next()
            print ".",
            if color_temp != last_ct or brightness != last_bri:
                last_bri = brightness
                last_ct = color_temp
                #if s == 17: # button 2 is auto
                light.send(dict(ct=color_temp, bri=brightness, on=True))
                print "\n%s; %dK; %.1f%% tap=%d" % (datetime.now().strftime("%a %H:%M:%S"), MIREK/color_temp, brightness/2.55, s),
            stdout.flush()
            sleep(2.0)
        sleep(1.0)


if __name__ == "__main__":
    from misc import lamp, attenuator
    from config import LOCAL_HUE_API, BRI_SINUS_CHARGE
    from extended_cct import extend_cct
    from phase import phase, sinus, charge, constant
    bri_phase_map = sinus(charge(BRI_SINUS_CHARGE))
    while True:
        tap1 = tap(LOCAL_HUE_API, 2)
        lights1 = extend_cct(lamp(LOCAL_HUE_API + "/lights/1"))
        lights1 = extend_cct(lamp(LOCAL_HUE_API + "/groups/0"))
        #weather1 = weather("http://api.wunderground.com/api/%s/conditions/q/pws:IUTRECHT57.json" % WUNDERGROUND_API_KEY)
        try:
            loop(lights1, tap1, bri_phase_map)
        except:
            from traceback import print_exc
            print_exc()
            sleep(5)
