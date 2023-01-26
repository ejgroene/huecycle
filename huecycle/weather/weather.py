
from misc import time822, average, lamp, attenuator, interpolate, autostart

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
            print("Weather: %s, next update: +%ds (%s);" % (last_observation["weather"].lower(), delta_t, last_observation["observation_time"]))
        yield CONDITIONS.get(last_observation["weather"].lower())
