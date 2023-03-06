import logging
logging.captureWarnings(True) # get rid of unverified https certificate
logging.basicConfig(level=logging.ERROR)

import time
from extended_cct import ct_to_xy
from jsonwalk import walk, ignore_silently

import autotest
test = autotest.get_tester(__name__)


import bridge
b = bridge.bridge(
    baseurl='https://192.168.178.78',
    username="IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt" # hue-application-key
)



def get_name(data, index={}):
    """ finds a human readable name for a given event or resource """
    type = data.get('type', '?')
    if name := data.get('metadata', {}).get('name'):
        pass
    elif owner := index.get(data.get('owner', {}).get('rid')):
        if name := owner.get('metadata', {}).get('name'):
            pass
    if group := data.get('group', {}).get('rtype' , ''):
        return f"{type}:{group}:{name}"
    return f"{type}:{name}"
    

@test
def get_name_from_metadata():
    """ NB:
        1. find unique qualified name for ease of use
        2. some resources are not unique:
           a. scene:zone:Energize (gets copied to multiple zones or rooms)
           b. behavior_script:Motion_sensor ?
           c. maybe more
        3. as long as the ones you actually use are unique, it's OK.
    """
    test.eq('A:jan', get_name({'metadata': {'name': 'jan'}, 'type': 'A'}))
    test.eq('A:Jo', get_name({'metadata': {'abcd': 'jan'}, 'type': 'A', 'owner': {'rid': 'id0'}},
                              {'id0': {'metadata': {'name': 'Jo'}}}))
    test.eq('?:jan', get_name({'owner': {'rid': 'id0'}}, {'id0': {'metadata': {'name': 'jan'}}}))
    test.eq('?:None', get_name({'owner': {'rid': 'id0'}}, {'id0': {'no-meta': {'name': 'jan'}}}))
    test.eq('A:jan', get_name({'owner': {'rid': 'id0'}, 'type': 'A'},
                              {'id0': {'metadata': {'name': 'jan'}, 'type': 'B'}}))


print('=========================== bridge objects ===================================')
b.read_objects()
byname = {}
for r in b.index.values():
    if qname := get_name(r, b.index):
        print(repr(qname), r['id'])
        if qname in byname:
            print(test.diff2(byname[qname], r))
            raise Exception("Duplicate name")
        byname[qname] = r
print('==============================================================================')

DEFAULT_CT = 1000000//4000
DIM_CT = 1000000//3000

def get_event(e):
    etype = e.get('type')
    if etype in e:
        return etype, e[etype]
    return etype, {k:v for k,v in e.items() if k not in 'type owner id_v1'}

office = byname['grouped_light:Office']

def office_on(brightness=100, ct=DEFAULT_CT):
    office.put({
        'on': {'on': True},
        'color_temperature': {'mirek': ct},
        'dimming': {'brightness': brightness}
    })

def office_off():
    office.put({'on': {'on': False}})


t1 = 0
press = None
for event in b.eventstream():
    qname = get_name(event, b.index)
    etype, event_data = get_event(event)
    print(f"{qname!r}: {dict(event_data)}")
    t0 = t1
    t1 = time.monotonic()
    if qname == 'button:Buro Dumb Button':
        last_press = press
        press = event_data['last_event']
        if press == 'initial_press':
            if last_press == 'short_release' and t1-t0 < 1:
                office_on()
            else:
                office_on(brightness=50, ct=DIM_CT)
        elif press == 'long_press':
            office_off()
    else:
        """ update internal state to reflect changes """
        resource = b.index[event['id']]
        old = set(resource.keys())
        resource.update(event)
        new = set(resource.keys())
        assert old == new, old ^ new
        

