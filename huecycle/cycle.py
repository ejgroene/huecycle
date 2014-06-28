#!/usr/bin/env python
import requests, json, time, datetime, math, ephem, sys
from misc import autostart
from config import WUNDERGROUND_API_KEY, LOCAL_HUE_API

def phase_factor(phase, boost=2.):
    angle = math.sin(math.pi * phase)
    return (1 - math.exp(-boost * angle)) / (1 - math.exp(-boost))

def color_mired(factor, upperbound=153):
    return int((1. - factor) * (500 - upperbound) + upperbound) # convert to Mirek (500/MK=2000K - 153/MK=6500K)

@autostart
def lamp_group(url):
    while True:
        args = yield
        r = requests.put(url, json.dumps(args))
        result = r.json
        if not u"success" in result[0]:
            print result

def weather(url):
    CONDITIONS = {  # 1.0 => Tmax = 4000 K,  0.0 => Tmax = 6500 K
        "scattered clouds": 1.0,
        "partly cloudy": 0.5,
        "mostly cloudy": 0.5,
        "light rain": 0.0,
        "patches of fog": 0.0,
        "clear": 1.0,
        "overcast": 0.0,
        "drizzle": 0.0,
        "heavy drizzle": 0.0,
        "rain": 0.0,
    }
    while True:
        r = requests.get(url)
        data = r.json
        weather = data["current_observation"]["weather"].lower()
        print weather, ";", CONDITIONS.get(weather),
        yield CONDITIONS.get(weather)

def sunphase(lat, lon, horizon, boost):
    ede = ephem.Observer()
    ede.horizon = str(horizon) # include civil twilight
    ede.lat, ede.lon = str(lat), str(lon)
    while True:
        t_now = ede.date
        ede.date = datetime.date.today() # set to only date, so next_* will always be today
        t_rise = ede.next_rising(ephem.Sun())
        t_set = ede.next_setting(ephem.Sun())
        phase = (t_now + 0. - t_rise + 0.) / (t_set + 0. - t_rise + 0.)
        print phase, ";",
        yield phase_factor(phase, boost)

def dayphase(start, end, boost):
    while True:
        now = datetime.datetime.now()
        phase = ((now.hour + now.minute/60.) - start) / (end - start)
        print phase, ";",
        yield phase_factor(phase, boost=boost)

def step(group, weather, day, sun):
    spf = sun.next()
    dpf = day.next()
    wpf = 0.
    on = 0. < dpf <= 1. or 0. < spf <= 1.
    if on: # avoid wunderground rate limit of 500/day
        wpf = weather.next()
    # if drizzle: hue=31000, sat=255
    color_temp = color_mired(spf, upperbound=(250-153)*wpf+153) # 250 mirek = 4000 K
    color_temp_in_K = 1000000 / color_temp
    brightness = int(max(0., 255. * dpf))
    print ";", datetime.datetime.now().strftime("%H:%M:%S"), ";", color_temp_in_K, ";", brightness, ";"
    sys.stdout.flush()
    group.send({"ct": color_temp, "bri": brightness, "on": on})

if __name__ == "__main__":
    group1 = lamp_group(LOCAL_HUE_API + "groups/0/action")
    weather1 = weather("http://api.wunderground.com/api/%s/conditions/q/pws:IUTRECHT57.json" % WUNDERGROUND_API_KEY)
    day1 = dayphase(7.5, 22.5, 3.0)
    sun1 = sunphase(-6, 52.053055, 5.638889, 1.0)
    while True:
        step(group1, weather1, day1, sun1)
        time.sleep(180) # avoid wunderground rate limit of 500/day
