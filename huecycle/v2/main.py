import logging
logging.captureWarnings(True) # get rid of unverified https certificate
logging.basicConfig(level=logging.ERROR)

import time
import bridge
import utils
import autotest
test = autotest.get_tester(__name__)


b = bridge.bridge(
    baseurl='https://192.168.178.78',
    username="IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt" # hue-application-key,
)
b.read_objects()
byname = b.byname()
utils.print_overview(b)


DEFAULT_CT = 1000000//4000
DIM_CT = 1000000//3000


office = byname['grouped_light:Office']
motion = byname['motion:Hue motion sensor 1']
lightl = byname['light_level:Hue motion sensor 1']
button = byname['button:Buro Dumb Button']


def office_on(brightness=100, ct=DEFAULT_CT):
    office.put({
        'on': {'on': True},
        'color_temperature': {'mirek': ct},
        'dimming': {'brightness': brightness}
    })

def office_off():
    office.put({'on': {'on': False}})


t_now = 0
t_last_on_motion = None
press = None
for service, update in b.eventstream():
    print(f"{service.qname!r}: {dict(update)}")
    t_last = t_now
    t_now = time.monotonic()
    if service == button:
        last_press = press
        press = update['last_event']
        if press == 'initial_press':
            if last_press == 'short_release' and t_now - t_last < 1:
                office_on()
            else:
                office_on(brightness=50, ct=DIM_CT)
        elif press == 'long_press':
            office_off()
    elif service == motion:
        if update.get('motion'): # could also be 'sensitivity'
            t_last_on_motion = t_now
            if not office.on.on:
                if lightl.light.light_level < 15000:
                    office_on(brightness=50, ct=DIM_CT)
                else:
                    office_on()
    else:
        """ update internal state to reflect changes """
        old = service.keys()
        service.update(update)
        diff = old ^ service.keys()
        assert diff <= {'temperature_valid'}, diff

    # TODO this should be triggered separately
    if t_last_on_motion and t_now - t_last_on_motion > 5 * 60:
        t_last_on_motion = None
        if office.on.on:
            office_off()
        

