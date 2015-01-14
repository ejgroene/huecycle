#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sys import stdout, argv
from time import sleep
from datetime import datetime, time, timedelta
from tap import tap, BUTTON1, BUTTON2, BUTTON3, BUTTON4
from alarm import alarm
from misc import lamp, autotest
from config import LOCAL_HUE_API
from itertools import izip
from phase import phase, sinus, charge, constant
from sunphase import get_ct_phase, rise_and_set, MIREK
from controllers import turn_on_at_dawn, turn_on_at_dusk, turn_off

light = lamp(LOCAL_HUE_API + "/lights/1")
t_wake = time(7,15)
t_sleep = time(22,15)
sun_dawn_and_dusk = rise_and_set(52.053055, 5.638889, -6.0) # civil twilight is at -6°
sun_rise_and_set = rise_and_set(52.053055, 5.638889, -0.0) 
sun_twilight_zones = rise_and_set(52.053055, 5.638889, 6.0)

begin_dawn = lambda: sun_dawn_and_dusk.next()[0]
end_dawn = lambda: sun_twilight_zones.next()[0]
begin_dusk = lambda: sun_twilight_zones.next()[1]
end_dusk = lambda: sun_dawn_and_dusk.next()[1]

from requests import post, get, delete
from json import dumps

rules = get(LOCAL_HUE_API + "/rules")
for rule in rules.json:
    print "deleting rule %s" % rule
    delete(LOCAL_HUE_API + "/rules/%s" % rule)

def create_rule(name, tapid, button, lights, **action):
    r = post(LOCAL_HUE_API + "/rules",
        dumps({
            "name":       name,
            "conditions": [dict(address="/sensors/%s/state/buttonevent" % tapid, operator="eq", value=str(button)),
                           dict(address="/sensors/%s/state/lastupdated" % tapid, operator="dx")],
            "actions":    [dict(address="%s/state" % lights, method="PUT", body=action)]
        }))
    assert r.status_code == 200, r.status_code

create_rule("Turn OFF", 2, BUTTON1, "/lights/1", on=False)
create_rule("Turn ON default", 2, BUTTON2, "/lights/1", on=True)
create_rule("Turn ON full", 2, BUTTON4,  "/lights/1", on=True, bri=255)

def loop(light, tap, bri_phase_map):
    last_bri = last_ct = 0
    while True:
        t_rise, t_set = sun_dawn_and_dusk.next()
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
                if s == BUTTON3:
                    light.send(dict(ct=color_temp, bri=brightness))
                    print "\n%s; %dK; %.1f%% tap=%d" % (datetime.now().strftime("%a %H:%M:%S"), MIREK/color_temp, brightness/2.55, s),
            stdout.flush()
            sleep(2.0)
        sleep(1.0)


if __name__ == "__main__":
    from misc import lamp, attenuator
    from config import LOCAL_HUE_API, BRI_SINUS_CHARGE
    from extended_cct import extend_cct
    from phase import phase, sinus, charge, constant
    alarm(
        turn_on_at_dawn(light, t_wake, begin_dawn),
        turn_on_at_dusk(light, t_sleep, begin_dusk),
        turn_off(light, end_dawn),
        turn_off(light, lambda: time(23,59))
        )

    bri_phase_map = sinus(charge(BRI_SINUS_CHARGE))
    while True:
        tap1 = tap(LOCAL_HUE_API, 2)
        #lights1 = extend_cct(lamp(LOCAL_HUE_API + "/lights/1"))
        lights1 = extend_cct( lamp(LOCAL_HUE_API + "/groups/0"))
        #weather1 = weather("http://api.wunderground.com/api/%s/conditions/q/pws:IUTRECHT57.json" % WUNDERGROUND_API_KEY)
        try:
            loop(lights1, tap1, bri_phase_map)
        except:
            from traceback import print_exc
            print_exc()
            sleep(5)
