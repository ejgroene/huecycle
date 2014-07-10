#!/usr/bin/env python
import requests, json, time, datetime, sys, rfc822
from misc import time822, average, lamp, attenuator, interpolate
from config import WUNDERGROUND_API_KEY, LOCAL_HUE_API
from traceback import print_exc
from extended_cct import extend_cct
from dayphase import dayphase
from sunphase import sunphase, CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT, CCT_OVERCAST_SKY

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

def loop(light, weather, day, sun):
    last_bri = last_ct = 0
    while True:
        try:
            spf = sun.next()
            dpf = day.next()
            wpf = weather.next()
            if dpf > 0.:    # day
                if spf > 0.:    # summer
                    ctpf = (spf + dpf) / 2
                    color_temp = int(interpolate(0., 1., ctpf, CCT_SUN_RISE, CCT_AVG_SUMMER_SUNLIGHT + wpf * OVERCAST_PLUS))
                else:           # winter
                    raise Exception("NYI")
            else:           # night
                color_temp = int(interpolate(0., 1., -dpf, 1000, 10000))
                color_temp
                #if spf > 0.:    # summer
                #    pass
                #else:           # winter
                #    raise Exception("NYI")
            brightness = int(max(0., 255. * dpf)) # always hard linked to day/night
            if color_temp != last_ct or brightness != last_bri:
                last_bri = brightness
                last_ct = color_temp
                print dpf, spf, datetime.datetime.now().strftime("%H:%M:%S"), "; %dK; %.1f%%" % (color_temp, brightness/2.55)
            light.send(dict(ct=color_temp, bri=brightness))
        except:
            print_exc()
        sys.stdout.flush()
        time.sleep(1.0)
    yield


if __name__ == "__main__":
    group1 = lamp(LOCAL_HUE_API + "groups/0/action")
    light1 = extend_cct(attenuator(group1))
    #lamp1 = lamp(LOCAL_HUE_API + "lights/1/state")
    #light1 = extend_cct(lamp1)
    weather1 = weather("http://api.wunderground.com/api/%s/conditions/q/pws:IUTRECHT57.json" % WUNDERGROUND_API_KEY)
    day1 = dayphase(7.0, 22.5, 2.0)
    sun1 = sunphase(52.053055, 5.638889, -6.0, boost=None)
    loop(light1, weather1, day1, sun1).next()
