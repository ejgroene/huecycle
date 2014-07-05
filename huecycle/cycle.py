#!/usr/bin/env python
import requests, json, time, datetime, math, ephem, sys, rfc822
from misc import autostart, time822, average
from config import WUNDERGROUND_API_KEY, LOCAL_HUE_API

def phase_factor(phase, boost=2.):
    angle = math.sin(math.pi * phase)
    return (1 - math.exp(-boost * angle)) / (1 - math.exp(-boost))

def color_mired(factor, upperbound=153):
    return int((1. - factor) * (500 - upperbound) + upperbound) # convert to Mirek (500/MK=2000K - 153/MK=6500K)

@autostart
def lamp_group(url):
    while True:
        ct, bri, on = yield
        result = requests.put(url, json.dumps({"ct": ct, "bri": bri, "on": on})).json
        if not "success" in result[0]:
            print result[0]

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
        "light rain showers": 1.0
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

def dayphase(start, end, boost):
    while True:
        now = datetime.datetime.now()
        phase = ((now.hour + now.minute/60.) - start) / (end - start)
        yield phase_factor(phase, boost=boost)

def loop(group, weather, day, sun):
    last_bri = last_ct = 0
    while True:
        try:
            spf = sun.next()
            dpf = day.next()
            wpf = 0.
            on = 0. < dpf <= 1. or 0. < spf <= 1.
            wpf = weather.next()
            # if drizzle: hue=31000, sat=255
            color_temp = color_mired(spf, upperbound=(250-153)*wpf+153) # 250 mirek = 4000 K
            brightness = int(max(0., 255. * dpf))
            if color_temp != last_ct or brightness != last_bri:
                last_bri = brightness
                last_ct = color_temp
                print datetime.datetime.now().strftime("%H:%M:%S"), "; %dK; %.1f%%" % (1000000/color_temp, brightness/2.55)
            group.send((color_temp, brightness, on))
        except Exception, e:
            print e
        time.sleep(1)
        sys.stdout.flush()
    yield


if __name__ == "__main__":
    group1 = lamp_group(LOCAL_HUE_API + "groups/0/action")
    weather1 = weather("http://api.wunderground.com/api/%s/conditions/q/pws:IUTRECHT57.json" % WUNDERGROUND_API_KEY)
    day1 = dayphase(7.5, 22.5, 3.0)
    sun1 = sunphase(52.053055, 5.638889, -6.0, 2.0)
    loop(group1, weather1, day1, sun1).next()
