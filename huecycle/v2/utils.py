
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

