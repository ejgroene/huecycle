#!/usr/bin/env python
import requests, json, time, datetime, math, ephem, sys, rfc822
from misc import autostart, time822, average, lamp, attenuator, interpolate
from config import WUNDERGROUND_API_KEY, LOCAL_HUE_API
from traceback import print_exc
from extended_cct import extend_cct
from dayphase import dayphase

def phase_factor(phase, boost=2.):
    angle = math.sin(math.pi * phase)
    return (1 - math.exp(-boost * angle)) / (1 - math.exp(-boost))

def weather(url):
    CONDITIONS = {  # 1.0 => Tmax = 4000 K,  0.0 => Tmax = 6500 K
        "clear": 0.0,
        "scattered clouds": 0.0,
        "partly cloudy": 0.25,
        "mostly cloudy": 0.5,
        "patches of fog": 0.75,
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

def sunphase(lat, lon, horizon, boost):
    while True:
        ede = ephem.Observer()
        ede.horizon = str(horizon) # include civil twilight
        ede.lat, ede.lon = str(lat), str(lon)
        t_now = ede.date
        ede.date = datetime.date.today() # set to only date, so next_* will always be today
        t_rise = ede.next_rising(ephem.Sun())
        t_set = ede.next_setting(ephem.Sun())
        phase = (t_now + 0. - t_rise + 0.) / (t_set + 0. - t_rise + 0.)
        yield phase_factor(phase, boost)

def loop(light, weather, day, sun):
    last_bri = last_ct = 0
    while True:
        try:
            spf = sun.next()
            dpf = day.next()
            wpf = weather.next()
            if dpf > 0.:    # day
                if spf > 0.:    # summer
                    color_temp = int(interpolate(0., 1., spf, 2000, 5500 + wpf * 1000))
                else:           # winter
                    raise Exception("NYI")
            else:           # night
                if spf > 0.:    # summer
                    color_temp = interpolate(0., 1., -dpf, 1000, 10000)
                else:           # winter
                    raise Exception("NYI")
            brightness = int(max(0, 255. * dpf)) # always hard linked to day/night
            if color_temp != last_ct or brightness != last_bri:
                last_bri = brightness
                last_ct = color_temp
                print dpf, datetime.datetime.now().strftime("%H:%M:%S"), "; %dK; %.1f%%" % (color_temp, brightness/2.55)
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
    day1 = dayphase(7.0, 22.5, 3.0)
    sun1 = sunphase(52.053055, 5.638889, -6.0, 2.0)
    loop(light1, weather1, day1, sun1).next()
