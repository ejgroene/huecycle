import autotest
test = autotest.get_tester(__name__)


def print_overview(bridge):
    def print_series(pre, series, seen, indent):
        for ref in series:
            resource = bridge.index[ref['rid']]
            print_one(pre, resource, seen, indent+'  ')

    def print_one(pre, resource, seen, indent=''):
        print(f"{indent}{pre}{resource.qname!r}")
        if resource.id not in seen:
            seen.add(resource.id)
            indent += '  '
            print_series('service: ', resource.get('services', ()), seen, indent)
            print_series('child: ', resource.get('children', ()), seen, indent)

    seen = set()
    print('==== available bridge objects ====')
    for resource in bridge.index.values():
        if resource['id'] not in seen:
            print_one('', resource, seen)
    print('==================================')


def get_name(data):
    return data.get('metadata', {}).get('name') if data else None


def get_qname(data, index={}):
    """ finds a unique human readable name for a given event or resource """
    type = data['type']
    if not (name := get_name(data)):
        if owner := data.get('owner'):
            resource = index.get(owner.get('rid'))
            name = get_name(resource)
    if group := data.get('group'):
        resource = index.get(group.get('rid'))
        qualifier = get_qname(resource, index)
        return f"{type}:{qualifier}:{name}"
    if control_id := data.get('metadata', {}).get('control_id'):
        return f"{type}:{name}:{control_id}"
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
    test.eq('A:jan', get_qname({'metadata': {'name': 'jan'}, 'type': 'A'}))
    test.eq('A:Jo', get_qname({'metadata': {'abcd': 'jan'}, 'type': 'A', 'owner': {'rid': 'id0'}},
                              {'id0': {'metadata': {'name': 'Jo'}}}))
    test.eq('A:jan', get_qname({'owner': {'rid': 'id0'}, 'type': 'A'},
                              {'id0': {'metadata': {'name': 'jan'}, 'type': 'B'}}))
    test.eq('A:jan:1', get_qname({'owner': {'rid': 'id0'}, 'type': 'A', 'metadata': {'control_id': 1}}, # Hue Tap
                              {'id0': {'metadata': {'name': 'jan'}, 'type': 'B'}}))


# keep other stuff here for reference

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


def find_color_temperature_limits(group, index):
    found_min = 0
    found_max = 1000
    owner = index[group['owner']['rid']]
    for child_ref in (r for r in owner['children'] if r['rtype'] == 'device'):
        child = index[child_ref['rid']]
        for light_ref in (r for r in child['services'] if r['rtype'] == 'light'):
            light = index[light_ref['rid']]
            schema = light['color_temperature']['mirek_schema']
            mirek_min = schema['mirek_minimum']
            mirek_max = schema['mirek_maximum']
            found_min = max(found_min, mirek_min)
            found_max = min(found_max, mirek_max)
    return found_min, found_max


@test
def find_color_temperature_limits_test():
    group  = {"id": "841634ec-253c-4830-9070-76c65ad09c84",
              "owner": { "rid": "bf012818-6e32-4d14-b505-e70c620f4d50", "rtype": "room" },
              "on": { "on": True },
              "dimming": { "brightness": 0.39 },
              "color_temperature": {},
              "type": "grouped_light"}
    owner  = {"id": "bf012818-6e32-4d14-b505-e70c620f4d50",
             "children": [ { "rid": "f9cfcdf4-d556-4065-b5ff-70b6bac02859", "rtype": "device" },
                           { "rid": "1e202743-3d02-4f19-be19-16ff95dc641f", "rtype": "device" },
                           { "rid": "1e202743-XXXX-4f19-be19-16ff95dc641f", "rtype": "something" }]}
    devic0 = {"id": "f9cfcdf4-d556-4065-b5ff-70b6bac02859",
              "services": [ { "rid": "030ec972-79b2-4fee-a207-2c739a4a1d14", "rtype": "light" },
                            { "rid": "030ec972-YYYY-4fee-a207-2c739a4a1d14", "rtype": "burp" }, ],
              "type": "device"}
    devic1 = {"id": "1e202743-3d02-4f19-be19-16ff95dc641f",
              "services": [ { "rid": "20f9e079-b120-4dfd-98f8-760ecab5fc4a", "rtype": "light" }, ],
              "type": "device"}
    light0 = {"id": "030ec972-79b2-4fee-a207-2c739a4a1d14",
              "color_temperature": { "mirek": 160,
                                     "mirek_valid": True,
                                     "mirek_schema": { "mirek_minimum": 166, "mirek_maximum": 555 } },
              "type": "light"}
    light1 = {"id": "20f9e079-b120-4dfd-98f8-760ecab5fc4a",
              "color_temperature": { "mirek": 160,
                                     "mirek_valid": True,
                                     "mirek_schema": { "mirek_minimum": 153, "mirek_maximum": 454 } },
              "type": "light"}
    index = {}
    index[owner['id']] = owner
    index[devic0['id']] = devic0
    index[devic1['id']] = devic1
    index[light0['id']] = light0
    index[light1['id']] = light1
    test.eq((166, 454), find_color_temperature_limits(group, index))
