#!/usr/bin/env python
import requests, json, sys, rfc822
from time import sleep
from datetime import datetime, time
from misc import time822, average, lamp, attenuator, interpolate, autostart
from config import WUNDERGROUND_API_KEY, LOCAL_HUE_API
from traceback import print_exc
from extended_cct import extend_cct
from sunphase import rise_and_set
from phase import phase, unity as linear
from math import sin, pi

# http://www.apogeephoto.com/july2004/jaltengarten7_2004.shtml
CCT_SUN_RISE = 2000
CCT_SUN_RISE_PLUS_1 = 3500
CCT_EARLY_MORNING_LATE_AFTERNOON = 4300
CCT_AVG_SUMMER_SUNLIGHT = 5400
CCT_OVERCAST_SKY = 6000

def weather(url):
    CONDITIONS = {  # 1.0 => Tmax = 4000 K,  0.0 => Tmax = 6500 K
        "clear": 0.0,
        "scattered clouds": 0.0,
        "partly cloudy": 0.25,
        "mostly cloudy": 0.5,
        "patches of fog": 0.75,
        "mist": 0.75,
        "light drizzle": 1.0,
        "drizzle": 1.0,
        "heavy drizzle": 1.0,
        "light rain": 1.0,
        "light rain showers": 1.0,
        "rain": 1.0,
        "overcast": 1.0,
    }
    last_observation = None
    last_observation_time = delta_t = 0.
    avg_delta_t = average()
    while True:
        now = time.time()
        if now > last_observation_time + delta_t:
            last_observation = requests.get(url).json["current_observation"]
            last_observation_time = time822(last_observation["observation_time_rfc822"])
            delta_t =  avg_delta_t.send(2 * (now - last_observation_time))
            print "Weather: %s, next update: +%ds (%s);" % (last_observation["weather"].lower(), delta_t, last_observation["observation_time"])
        yield CONDITIONS.get(last_observation["weather"].lower())

OVERCAST_PLUS = CCT_OVERCAST_SKY - CCT_AVG_SUMMER_SUNLIGHT

@autostart
def sinus():
    x = 0.
    while True:
        x = yield sin(x * pi)

def loop(light, weather):
    last_bri = last_ct = 0
    sun = rise_and_set(52.053055, 5.638889, -6.0)
    while True:
        t_rise, t_set = sun.next()
        t_now = datetime.now()
        t_wake, t_sleep = datetime.combine(t_now, time(7,15)), datetime.combine(t_now, time(22,15))

        t_day_begin = max(t_rise, t_wake)
        t_day_end = min(t_set, t_sleep)
        t_night_begin = max(t_set, t_sleep)
        t_night_end = min(t_rise, t_wake)

        if t_day_begin < t_now < t_day_end:
            ct_cycle = phase(t_day_begin, t_day_end, sinus(), 2000, 5400)
        elif t_night_begin < t_now < t_night_end:
            ct_cycle = phase(t_night_begin, t_night_end, sinus(), 1000, 10000)
        elif t_night_end < t_now < t_day_begin:
            ct_cycle = phase(t_night_end, t_day_begin, linear(), 1000, 2000)
        elif t_day_end < t_now < t_night_begin:
            ct_cycle = phase(t_day_end, t_night_begin, linear(), 2000, 1000)
        else:
            raise Exception("foutje")

        color_temp = ct_cycle.next()

        bri_cycle = phase(t_wake, t_sleep, sinus(), 0, 255)
        brightness = int(max(0., bri_cycle.next())) # always hard linked to day/night
        if color_temp != last_ct or brightness != last_bri:
            last_bri = brightness
            last_ct = color_temp
            print "%s; %dK; %.1f%%" % (t_now, color_temp, brightness/2.55)
        light.send(dict(ct=color_temp, bri=brightness))
        sys.stdout.flush()
        sleep(1.0)
    yield


if __name__ == "__main__":
    group1 = lamp(LOCAL_HUE_API + "groups/0/action")
    light1 = extend_cct(attenuator(group1))
    #lamp1 = lamp(LOCAL_HUE_API + "lights/1/state")
    #light1 = extend_cct(lamp1)
    weather1 = weather("http://api.wunderground.com/api/%s/conditions/q/pws:IUTRECHT57.json" % WUNDERGROUND_API_KEY)
    loop(light1, weather1).next()
