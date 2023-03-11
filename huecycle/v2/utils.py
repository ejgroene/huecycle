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

