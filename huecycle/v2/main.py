import logging
import autotest
from autotest.prrint import prrint
from prototype3 import prototype
import requests
from pprint import pprint
from functools import partial
import json
import time
from extended_cct import ct_to_xy
from jsonwalk import walk, ignore_silently

test = autotest.get_tester(__name__)

logging.captureWarnings(True) # get rid of unverified https certificate
logging.basicConfig(level=logging.ERROR)

baseurl='https://192.168.178.78'
username="IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt" # hue-application-key

class bridge(prototype):

    index = {}
    types = {}
    apiv2 = f"{baseurl}/clip/v2"
    apiv1 = f"{baseurl}/api/{username}"
    headers={'hue-application-key': username}
    http_get = partial(requests.get, verify=False, headers=headers)
    http_put = partial(requests.put, verify=False, headers=headers)

    def put(self, data):
        path = f'{self.apiv2}/resource/{self.type}/{self.id}'
        r = self.http_put(path, json=data)
        """ We might as well ignore the response, as it sometimes gives 429 with
            'Oops, there appears to be no lighting here', and it gives 200 without 
            actually doing something.
        """
        if r.status_code != 200:
            print(f"Error (ignored): {path} {data} {r.text}")

    def _get(self):
        path = f'{self.apiv2}/resource/{self.type}/{self.id}'
        r = self.http_get(path)
        assert r.status_code == 200, (path, r)
        return self(self.type, **r.json()['data'][0])

    def read_objects(self):
        path = f"{self.apiv2}/resource"
        r = self.http_get(path)
        assert r.status_code == 200, (path, r)
        for data in r.json()['data']:
            resource = self(data['type'], **data)
            self.index[resource.id] = resource
            self.types.setdefault(resource.type, {})[resource.id] = resource

    def read_rules(self):
        r = self.http_get(f"{self.apiv1}/rules")
        self.rules = r.json()
        return self.rules
        
    def lights(self):
        return self.index['light'].values()

    def eventstream(self):
        """ do not use SSEClient, it is buggy, just use long polling """
        while True:
            try:
                response = self.http_get(f"{baseurl}/eventstream/clip/v2", timeout=100)
            except requests.exceptions.ReadTimeout:
                print('ping')
                continue
            assert response.status_code == 200
            for event in response.json():
                for data in event['data']:
                    yield prototype(data['type'], **data)

def get_name(data, index={}):
    """ finds a human readable name for a given event or resource """
    type = data.get('type', '?')
    if name := data.get('metadata', {}).get('name'):
        return f"{type}:{name}"
    elif owner := index.get(data.get('owner', {}).get('rid')):
        if name := owner.get('metadata', {}).get('name'):
            return f"{type}:{name}"

@test
def get_name_from_metadata():
    test.eq('A:jan', get_name({'metadata': {'name': 'jan'}, 'type': 'A'}))
    test.eq('A:Jo', get_name({'metadata': {'abcd': 'jan'}, 'type': 'A', 'owner': {'rid': 'id0'}},
                              {'id0': {'metadata': {'name': 'Jo'}}}))
    test.eq('?:jan', get_name({'owner': {'rid': 'id0'}}, {'id0': {'metadata': {'name': 'jan'}}}))
    test.eq(None, get_name({'owner': {'rid': 'id0'}}, {'id0': {'no-meta': {'name': 'jan'}}}))
    test.eq('A:jan', get_name({'owner': {'rid': 'id0'}, 'type': 'A'},
                              {'id0': {'metadata': {'name': 'jan'}, 'type': 'B'}}))


print('=========================== bridge objects ===================================')
bridge.read_objects()
byname = {}
for rtype, resources in bridge.types.items():
    for uid in resources:
        r = bridge.index[uid]
        if qname := get_name(r, bridge.index):
            print(repr(qname), r['id'])
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
for event in bridge.eventstream():
    qname = get_name(event, bridge.index)
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
        resource = bridge.index[event['id']]
        old = set(resource.keys())
        resource.update(event)
        new = set(resource.keys())
        assert old == new, old ^ new
        




def print_device(device):
    print()
    print("Device {name!r} ({archetype})".format(**(device.metadata)))
    print(f"  {device.product_data['product_name']!r}  {device.id}  ({device.id_v1})")
    for s in device.services:
        print(f"  {s['rtype']}:  {s['rid']}")

def print_rule(rule):
    print()
    print(f"Rule {rule.id} of {rule.owner}")
    print("  if")
    for c in rule.conditions:
        print("    {address} {operator} {value}".format(**{'value':''} | c))
    print("  then")
    for a in rule.actions:
        print("    {method} {body} on {address}".format(**a))




#w = walk({
#    '__key__': lambda a, s, p, os: s['type'],
#    #'__switch__': lambda p, os: os['owner'],
#    'button': {
#       'last_event': {
#            'initial_press': lambda a, s, p, os: l1.put({'on': {'on': True}}), #prev == 'short_release' and evebt.t-prev.t < 0}})
#            'short_release': ignore_silently,
#            'long_press': ignore_silently,
#            'repeat': ignore_silently,
#            'long_release': ignore_silently,
#       },
#    },
#    '*': lambda a, *_: a,
#})

def color_profile_bulb():
    tolemeo = byname['light:Artemide']
    for T in range(153, 500+1):
        # x, y = ct_to_xy(T)
        tolemeo.put({'color_temperature': {'mirek': T}})
        time.sleep(1)
        updated = tolemeo._get()
        print(f"{updated.color_temperature.mirek}: {dict(updated.color.xy)}  # {T}")


